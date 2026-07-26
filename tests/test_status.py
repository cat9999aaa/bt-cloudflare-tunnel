from __future__ import annotations

from cf_tunnel.system_service import CloudflaredSystem, CommandResult


def test_inspect_reports_installed_version_and_active_service() -> None:
    def runner(command: list[str]) -> CommandResult:
        if command == ["cloudflared", "--version"]:
            return CommandResult(
                returncode=0, stdout="cloudflared version 2026.7.0", stderr=""
            )
        return CommandResult(returncode=0, stdout="", stderr="")

    status = CloudflaredSystem(runner=runner, package_manager=lambda: "apt").inspect()

    assert status.installed is True
    assert status.version == "cloudflared version 2026.7.0"
    assert status.service_active is True
