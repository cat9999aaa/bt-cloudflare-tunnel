from __future__ import annotations

from cf_tunnel.system_service import CloudflaredSystem, CommandResult


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, command: list[str]) -> CommandResult:
        self.commands.append(tuple(command))
        return CommandResult(returncode=0, stdout="ok", stderr="")


def test_apt_installer_uses_cloudflare_official_repository_without_user_input() -> None:
    runner = RecordingRunner()
    system = CloudflaredSystem(runner=runner, package_manager=lambda: "apt")

    result = system.install_package()

    assert result.success is True
    assert any("pkg.cloudflare.com" in " ".join(command) for command in runner.commands)
    assert runner.commands[-1] == ("apt-get", "install", "-y", "cloudflared")


def test_service_installer_passes_tunnel_token_as_a_single_process_argument() -> None:
    runner = RecordingRunner()
    system = CloudflaredSystem(runner=runner, package_manager=lambda: "apt")

    result = system.install_service("tunnel-token")

    assert result.success is True
    assert runner.commands == [("cloudflared", "service", "install", "tunnel-token")]
