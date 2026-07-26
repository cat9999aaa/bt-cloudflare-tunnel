from __future__ import annotations

from pathlib import Path
from typing import cast

from cf_tunnel.cf_tunnel_main import PluginDependencies, cf_tunnel_main
from cf_tunnel.cloudflare_api import (
    ConfigurationResult,
    DnsBinding,
    RemoteStatus,
    TunnelDetails,
    Zone,
)
from cf_tunnel.storage import ConfigStore
from cf_tunnel.system_service import CloudflaredStatus, OperationResult


class FakeSystem:
    def install_package(self) -> OperationResult:
        return OperationResult(True, "installed")

    def install_service(self, tunnel_token: str) -> OperationResult:
        return OperationResult(True, "service installed")

    def restart_service(self) -> OperationResult:
        return OperationResult(True, "restarted")

    def inspect(self) -> CloudflaredStatus:
        return CloudflaredStatus(
            installed=True, version="2026.7.0", service_active=True
        )


class FailingServiceSystem(FakeSystem):
    def install_service(self, tunnel_token: str) -> OperationResult:
        return OperationResult(False, "service install failed")


class SetupArgs:
    token: str = "secret-token"
    wildcard_domain: str = "*.dev.dashen.wang"


def fake_setup(_config: object) -> tuple[ConfigurationResult, str]:
    return (
        ConfigurationResult(
            zone=Zone(id="zone-id", name="dashen.wang", account_id="account-id"),
            tunnel=TunnelDetails(
                id="tunnel-id", name="bt-cf-dashen-wang", account_id="account-id"
            ),
            dns_binding=DnsBinding(
                hostname="*.dev.dashen.wang", target="tunnel-id.cfargotunnel.com"
            ),
        ),
        "tunnel-token",
    )


def fake_remote_status(_config: object) -> RemoteStatus:
    return RemoteStatus(tunnel_connected=True, dns_bound=True)


def dependencies(location: Path) -> PluginDependencies:
    return PluginDependencies(
        store=ConfigStore(location),
        system=FakeSystem(),
        setup=fake_setup,
        remote_status=fake_remote_status,
    )


def failing_service_dependencies(location: Path) -> PluginDependencies:
    return PluginDependencies(
        store=ConfigStore(location),
        system=FailingServiceSystem(),
        setup=fake_setup,
        remote_status=fake_remote_status,
    )


def status_data(payload: dict[str, object]) -> dict[str, object]:
    data = payload["data"]
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def test_unconfigured_plugin_status_is_safe_for_the_settings_page() -> None:
    payload = cf_tunnel_main(
        dependencies(Path("/tmp/does-not-exist-cf-tunnel.json"))
    ).get_status(object())

    assert payload["status"] is True
    data = status_data(payload)
    assert data["configured"] is False
    assert "token" not in str(data).lower()


def test_configure_installs_service_saves_configuration_and_masks_sensitive_values(
    tmp_path: Path,
) -> None:
    plugin = cf_tunnel_main(dependencies(tmp_path / "config.json"))

    payload = plugin.configure(SetupArgs())

    assert payload["status"] is True
    assert status_data(payload)["wildcard_domain"] == "*.dev.dashen.wang"
    assert "secret-token" not in str(payload)
    assert "tunnel-token" not in str(payload)


def test_configured_plugin_status_includes_cloudflare_tunnel_and_dns_health(
    tmp_path: Path,
) -> None:
    plugin = cf_tunnel_main(dependencies(tmp_path / "config.json"))
    _ = plugin.configure(SetupArgs())

    payload = plugin.get_status(object())

    data = status_data(payload)
    assert data["tunnel_connected"] is True
    assert data["dns_bound"] is True


def test_configure_keeps_remote_configuration_when_service_registration_fails(
    tmp_path: Path,
) -> None:
    location = tmp_path / "config.json"
    plugin = cf_tunnel_main(failing_service_dependencies(location))

    payload = plugin.configure(SetupArgs())

    assert payload["status"] is False
    saved = ConfigStore(location).load()
    assert saved is not None
    assert saved.tunnel_id == "tunnel-id"
