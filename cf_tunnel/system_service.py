from __future__ import annotations

import shutil
import subprocess
from typing import Callable, List, Optional

try:
    from .compat import frozen_dataclass
except ImportError:
    from compat import frozen_dataclass


@frozen_dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@frozen_dataclass
class OperationResult:
    success: bool
    message: str


@frozen_dataclass
class CloudflaredStatus:
    installed: bool
    version: str
    service_active: bool


Runner = Callable[[List[str]], CommandResult]
PackageManager = Callable[[], Optional[str]]


class CloudflaredSystem:
    """Installs and inspects cloudflared through fixed, user-input-free commands."""

    def __init__(
        self,
        runner: Runner | None = None,
        package_manager: PackageManager | None = None,
    ) -> None:
        self._runner: Runner = runner or self._run
        self._package_manager: PackageManager = (
            package_manager or self._detect_package_manager
        )

    def install_package(self) -> OperationResult:
        manager = self._package_manager()
        commands = self._installation_commands(manager)
        if commands is None:
            return OperationResult(
                False,
                "未识别到 apt、dnf 或 yum，请按 Cloudflare 官方文档手动安装 cloudflared",
            )

        for command in commands:
            result = self._runner(command)
            if result.returncode != 0:
                return OperationResult(
                    False, "cloudflared 安装失败，请检查系统软件源和外网连接"
                )
        return OperationResult(True, "cloudflared 安装完成")

    def install_service(self, tunnel_token: str) -> OperationResult:
        result = self._runner(["cloudflared", "service", "install", tunnel_token])
        if result.returncode != 0:
            return OperationResult(
                False, "Tunnel 服务注册失败，请检查 cloudflared 安装状态"
            )
        return OperationResult(True, "Tunnel 服务已注册")

    def restart_service(self) -> OperationResult:
        result = self._runner(["systemctl", "restart", "cloudflared"])
        if result.returncode != 0:
            return OperationResult(False, "Tunnel 服务重启失败，请检查 systemd 状态")
        return OperationResult(True, "Tunnel 服务已重启")

    def inspect(self) -> CloudflaredStatus:
        version_result = self._runner(["cloudflared", "--version"])
        installed = version_result.returncode == 0
        service_result = (
            self._runner(["systemctl", "is-active", "--quiet", "cloudflared"])
            if installed
            else CommandResult(1, "", "")
        )
        return CloudflaredStatus(
            installed=installed,
            version=version_result.stdout.strip() if installed else "",
            service_active=service_result.returncode == 0,
        )

    @staticmethod
    def _detect_package_manager() -> str | None:
        for manager in ("apt-get", "dnf", "yum"):
            if shutil.which(manager) is not None:
                return "apt" if manager == "apt-get" else manager
        return None

    @staticmethod
    def _installation_commands(manager: str | None) -> tuple[list[str], ...] | None:
        if manager == "apt":
            return (
                ["mkdir", "-p", "--mode=0755", "/usr/share/keyrings"],
                [
                    "curl",
                    "-fsSL",
                    "https://pkg.cloudflare.com/cloudflare-main.gpg",
                    "-o",
                    "/usr/share/keyrings/cloudflare-main.gpg",
                ],
                [
                    "/bin/sh",
                    "-c",
                    "printf '%s\\n' 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' > /etc/apt/sources.list.d/cloudflared.list",
                ],
                ["apt-get", "update"],
                ["apt-get", "install", "-y", "cloudflared"],
            )
        if manager in {"dnf", "yum"}:
            return (
                [
                    "curl",
                    "-fsSL",
                    "https://pkg.cloudflare.com/cloudflared.repo",
                    "-o",
                    "/etc/yum.repos.d/cloudflared.repo",
                ],
                [manager, "install", "-y", "cloudflared"],
            )
        return None

    @staticmethod
    def _run(command: list[str]) -> CommandResult:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
