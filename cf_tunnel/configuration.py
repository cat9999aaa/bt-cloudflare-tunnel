from __future__ import annotations

try:
    from .cloudflare_api import (
        CloudflareApiError,
        ConfigurationResult,
        DnsBinding,
        TunnelDetails,
        Zone,
    )
    from .domain import PluginConfig, WildcardDomain
except ImportError:
    from cloudflare_api import (
        CloudflareApiError,
        ConfigurationResult,
        DnsBinding,
        TunnelDetails,
        Zone,
    )
    from domain import PluginConfig, WildcardDomain


class TunnelApi:
    def resolve_zone(self, wildcard: WildcardDomain) -> Zone: ...

    def create_tunnel(self, zone: Zone, name: str) -> TunnelDetails: ...

    def put_ingress(self, tunnel: TunnelDetails, wildcard: WildcardDomain) -> None: ...

    def upsert_wildcard_cname(
        self, zone: Zone, tunnel: TunnelDetails, wildcard: WildcardDomain
    ) -> DnsBinding: ...


class ConfigurationService:
    """Creates the one wildcard Tunnel route used by all Baota development sites."""

    def __init__(self, client: TunnelApi) -> None:
        self._client = client

    def configure(self, config: PluginConfig) -> ConfigurationResult:
        account_id = config.account_id
        if account_id is None:
            raise CloudflareApiError("请先保存有效的 Cloudflare 帐户 ID")
        zone = self._client.resolve_zone(config.wildcard)
        if zone.account_id != account_id.value:
            raise CloudflareApiError("帐户 ID 与通配域名所属 Zone 不匹配")
        tunnel = self._saved_tunnel(config, zone) or self._client.create_tunnel(
            zone, "bt-cf-" + zone.name.replace(".", "-")
        )
        self._client.put_ingress(tunnel, config.wildcard)
        return ConfigurationResult(
            zone=zone,
            tunnel=tunnel,
            dns_binding=self._client.upsert_wildcard_cname(
                zone, tunnel, config.wildcard
            ),
        )

    @staticmethod
    def _saved_tunnel(config: PluginConfig, zone: Zone) -> TunnelDetails | None:
        account_id = config.account_id
        tunnel_id = config.tunnel_id
        tunnel_name = config.tunnel_name
        if (
            config.zone_id != zone.id
            or account_id is None
            or account_id.value != zone.account_id
            or tunnel_id is None
            or tunnel_name is None
        ):
            return None
        return TunnelDetails(
            id=tunnel_id,
            name=tunnel_name,
            account_id=account_id.value,
        )
