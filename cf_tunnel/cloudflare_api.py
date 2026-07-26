from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Protocol, TypeAlias, cast, final
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .domain import PluginConfig, WildcardDomain
except ImportError:
    from domain import PluginConfig, WildcardDomain

_API_BASE = "https://api.cloudflare.com/client/v4"
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
RequestOpener = Callable[[Request], Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class Zone:
    id: str
    name: str
    account_id: str


@dataclass(frozen=True, slots=True)
class TunnelDetails:
    id: str
    name: str
    account_id: str


@dataclass(frozen=True, slots=True)
class DnsBinding:
    hostname: str
    target: str


@dataclass(frozen=True, slots=True)
class RemoteStatus:
    tunnel_connected: bool
    dns_bound: bool


@dataclass(frozen=True, slots=True)
class ConfigurationResult:
    zone: Zone
    tunnel: TunnelDetails
    dns_binding: DnsBinding


@dataclass(frozen=True, slots=True)
class CloudflareApiError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


class TunnelApi(Protocol):
    def resolve_zone(self, wildcard: WildcardDomain) -> Zone: ...

    def create_tunnel(self, zone: Zone, name: str) -> TunnelDetails: ...

    def put_ingress(self, tunnel: TunnelDetails, wildcard: WildcardDomain) -> None: ...

    def upsert_wildcard_cname(
        self, zone: Zone, tunnel: TunnelDetails, wildcard: WildcardDomain
    ) -> DnsBinding: ...


@final
class CloudflareClient:
    """Small, token-safe client for the Cloudflare Tunnel and DNS endpoints."""

    def __init__(self, token: str, opener: RequestOpener | None = None) -> None:
        self._token: str = token
        self._opener: RequestOpener = opener or self._open

    @staticmethod
    def zone_from_values(zone_id: str, name: str, account_id: str) -> Zone:
        return Zone(id=zone_id, name=name, account_id=account_id)

    @staticmethod
    def tunnel_from_values(tunnel_id: str, name: str, account_id: str) -> TunnelDetails:
        return TunnelDetails(id=tunnel_id, name=name, account_id=account_id)

    def resolve_zone(self, wildcard: WildcardDomain) -> Zone:
        labels = wildcard.hostname.split(".")
        for index in range(len(labels) - 1):
            candidate = ".".join(labels[index:])
            payload = self._request("GET", "/zones?name=" + candidate)
            results = self._list_value(payload, "result")
            if results:
                return self._zone_from_api(self._object_value(results[0]))
        raise CloudflareApiError("找不到由当前 Token 管理的 Cloudflare Zone")

    def create_tunnel(self, zone: Zone, name: str) -> TunnelDetails:
        payload = self._request(
            "POST",
            "/accounts/" + zone.account_id + "/cfd_tunnel",
            {"name": name, "config_src": "cloudflare"},
        )
        result = self._object_value(payload["result"])
        return TunnelDetails(
            id=self._string_value(result, "id"),
            name=self._string_value(result, "name"),
            account_id=zone.account_id,
        )

    def get_tunnel_token(self, tunnel: TunnelDetails) -> str:
        payload = self._request(
            "GET",
            "/accounts/" + tunnel.account_id + "/cfd_tunnel/" + tunnel.id + "/token",
        )
        return self._string_value(payload, "result")

    def put_ingress(self, tunnel: TunnelDetails, wildcard: WildcardDomain) -> None:
        origin_request: JsonObject = {}
        ingress: list[JsonObject] = [
            {
                "hostname": wildcard.value,
                "service": "http://127.0.0.1:80",
                "originRequest": origin_request,
            },
            {"service": "http_status:404"},
        ]
        body: Mapping[str, object] = {"config": {"ingress": ingress}}
        _ = self._request(
            "PUT",
            "/accounts/"
            + tunnel.account_id
            + "/cfd_tunnel/"
            + tunnel.id
            + "/configurations",
            body,
        )

    def upsert_wildcard_cname(
        self, zone: Zone, tunnel: TunnelDetails, wildcard: WildcardDomain
    ) -> DnsBinding:
        target = tunnel.id + ".cfargotunnel.com"
        records = self._list_value(
            self._request(
                "GET",
                "/zones/" + zone.id + "/dns_records?type=CNAME&name=" + wildcard.value,
            ),
            "result",
        )
        body: Mapping[str, object] = {
            "type": "CNAME",
            "name": wildcard.value,
            "content": target,
            "proxied": True,
        }
        if records:
            record_id = self._string_value(self._object_value(records[0]), "id")
            _ = self._request(
                "PUT", "/zones/" + zone.id + "/dns_records/" + record_id, body
            )
        else:
            _ = self._request("POST", "/zones/" + zone.id + "/dns_records", body)
        return DnsBinding(hostname=wildcard.value, target=target)

    def get_remote_status(
        self, tunnel: TunnelDetails, zone_id: str, wildcard: WildcardDomain
    ) -> RemoteStatus:
        connections = self._list_value(
            self._request(
                "GET",
                "/accounts/"
                + tunnel.account_id
                + "/cfd_tunnel/"
                + tunnel.id
                + "/connections",
            ),
            "result",
        )
        records = self._list_value(
            self._request(
                "GET",
                "/zones/" + zone_id + "/dns_records?type=CNAME&name=" + wildcard.value,
            ),
            "result",
        )
        expected_target = tunnel.id + ".cfargotunnel.com"
        dns_bound = any(
            self._string_value(self._object_value(record), "content") == expected_target
            and self._object_value(record).get("proxied") is True
            for record in records
        )
        return RemoteStatus(tunnel_connected=bool(connections), dns_bound=dns_bound)

    def _request(
        self, method: str, path: str, body: Mapping[str, object] | None = None
    ) -> JsonObject:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            _API_BASE + path,
            data=data,
            headers={
                "Authorization": "Bearer " + self._token,
                "Content-Type": "application/json",
            },
            method=method,
        )
        payload = self._object_value(self._opener(request))
        if payload.get("success") is True:
            return payload
        raise CloudflareApiError(self._error_message(payload))

    @staticmethod
    def _open(request: Request) -> JsonObject:
        try:
            response = cast(HTTPResponse, urlopen(request, timeout=20))
            with response:
                response_body: bytes = response.read()
            payload = cast(object, json.loads(response_body.decode("utf-8")))
            return CloudflareClient._object_value(payload)
        except HTTPError as error:
            raise CloudflareApiError(
                "Cloudflare API 请求失败（HTTP " + str(error.code) + "）"
            ) from None
        except URLError:
            raise CloudflareApiError(
                "无法连接 Cloudflare API，请检查服务器外网连接"
            ) from None

    @staticmethod
    def _error_message(payload: Mapping[str, JsonValue]) -> str:
        errors = payload.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            message = errors[0].get("message")
            if isinstance(message, str):
                return "Cloudflare API：" + message
        return "Cloudflare API 返回了未知错误"

    @staticmethod
    def _list_value(payload: Mapping[str, JsonValue], key: str) -> list[JsonValue]:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        raise CloudflareApiError("Cloudflare API 返回格式异常")

    @staticmethod
    def _object_value(value: object) -> JsonObject:
        if isinstance(value, dict):
            return cast(JsonObject, value)
        raise CloudflareApiError("Cloudflare API 返回格式异常")

    @staticmethod
    def _string_value(payload: Mapping[str, JsonValue], key: str) -> str:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
        raise CloudflareApiError("Cloudflare API 返回格式异常")

    @classmethod
    def _zone_from_api(cls, payload: JsonObject) -> Zone:
        account = cls._object_value(payload.get("account"))
        return Zone(
            id=cls._string_value(payload, "id"),
            name=cls._string_value(payload, "name"),
            account_id=cls._string_value(account, "id"),
        )


@final
class ConfigurationService:
    """Creates the one wildcard Tunnel route used by all Baota development sites."""

    def __init__(self, client: TunnelApi) -> None:
        self._client = client

    def configure(self, config: PluginConfig) -> ConfigurationResult:
        zone = self._client.resolve_zone(config.wildcard)
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
            or account_id != zone.account_id
            or account_id is None
            or tunnel_id is None
            or tunnel_name is None
        ):
            return None
        return TunnelDetails(
            id=tunnel_id,
            name=tunnel_name,
            account_id=account_id,
        )
