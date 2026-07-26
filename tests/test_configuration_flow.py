from __future__ import annotations

import pytest

from cf_tunnel.cloudflare_api import CloudflareApiError, DnsBinding, TunnelDetails, Zone
from cf_tunnel.configuration import ConfigurationService
from cf_tunnel.domain import (
    PluginConfig,
    WildcardDomain,
    parse_cloudflare_account_id,
    parse_wildcard_domain,
)


class RecordingClient:
    def __init__(self, zone_account_id: str = "a" * 32) -> None:
        self.ingress_hostname: str = ""
        self.create_calls: int = 0
        self._zone_account_id = zone_account_id

    def resolve_zone(self, wildcard: WildcardDomain) -> Zone:
        return Zone(id="zone-id", name="dashen.wang", account_id=self._zone_account_id)

    def create_tunnel(self, zone: Zone, name: str) -> TunnelDetails:
        self.create_calls += 1
        return TunnelDetails(
            id="tunnel-id", name="bt-cf-dashen-wang", account_id=self._zone_account_id
        )

    def put_ingress(self, tunnel: TunnelDetails, wildcard: WildcardDomain) -> None:
        self.ingress_hostname = wildcard.value

    def upsert_wildcard_cname(
        self, zone: Zone, tunnel: TunnelDetails, wildcard: WildcardDomain
    ) -> DnsBinding:
        return DnsBinding(
            hostname=wildcard.value, target=tunnel.id + ".cfargotunnel.com"
        )


def test_configuration_flow_uses_one_wildcard_tunnel_and_cname() -> None:
    client = RecordingClient()
    service = ConfigurationService(client)
    config = PluginConfig(
        token="secret-token",
        wildcard=parse_wildcard_domain("*.dev.dashen.wang"),
        account_id=parse_cloudflare_account_id("a" * 32),
    )

    result = service.configure(config)

    assert client.ingress_hostname == "*.dev.dashen.wang"
    assert result.dns_binding.target == "tunnel-id.cfargotunnel.com"


def test_configuration_flow_reuses_the_saved_tunnel_for_the_same_zone() -> None:
    client = RecordingClient()
    service = ConfigurationService(client)
    config = PluginConfig(
        token="secret-token",
        wildcard=parse_wildcard_domain("*.dev.dashen.wang"),
        zone_id="zone-id",
        account_id=parse_cloudflare_account_id("a" * 32),
        tunnel_id="tunnel-id",
        tunnel_name="bt-cf-dashen-wang",
    )

    result = service.configure(config)

    assert client.create_calls == 0
    assert result.tunnel.id == "tunnel-id"


def test_configuration_flow_rejects_a_zone_from_another_account() -> None:
    service = ConfigurationService(RecordingClient(zone_account_id="b" * 32))
    config = PluginConfig(
        token="secret-token",
        wildcard=parse_wildcard_domain("*.dev.dashen.wang"),
        account_id=parse_cloudflare_account_id("a" * 32),
    )

    with pytest.raises(CloudflareApiError, match="帐户 ID"):
        _ = service.configure(config)
