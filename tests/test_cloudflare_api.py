from __future__ import annotations

import json
from urllib.request import Request

from cf_tunnel.cloudflare_api import CloudflareClient
from cf_tunnel.domain import parse_wildcard_domain


class FakeOpener:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.requests: list[Request] = []

    def __call__(self, request: Request) -> dict[str, object]:
        self.requests.append(request)
        return self._responses.pop(0)


def test_resolve_zone_walks_hostname_suffixes_until_token_managed_zone_is_found() -> (
    None
):
    opener = FakeOpener(
        [
            {"success": True, "result": []},
            {
                "success": True,
                "result": [
                    {
                        "id": "zone-id",
                        "name": "dashen.wang",
                        "account": {"id": "account-id"},
                    }
                ],
            },
        ]
    )
    client = CloudflareClient("secret-token", opener)

    zone = client.resolve_zone(parse_wildcard_domain("*.dev.dashen.wang"))

    assert zone.id == "zone-id"
    assert zone.account_id == "account-id"
    assert [request.full_url for request in opener.requests] == [
        "https://api.cloudflare.com/client/v4/zones?name=dev.dashen.wang",
        "https://api.cloudflare.com/client/v4/zones?name=dashen.wang",
    ]
    assert opener.requests[0].get_header("Authorization") == "Bearer secret-token"


def test_create_tunnel_and_wildcard_ingress_use_cloudflare_remote_configuration() -> (
    None
):
    opener = FakeOpener(
        [
            {
                "success": True,
                "result": {
                    "id": "tunnel-id",
                    "name": "bt-cf-dashen-wang",
                    "account_tag": "account-id",
                },
            },
            {"success": True, "result": {}},
        ]
    )
    client = CloudflareClient("secret-token", opener)
    zone = client.zone_from_values("zone-id", "dashen.wang", "account-id")

    tunnel = client.create_tunnel(zone, "bt-cf-dashen-wang")
    client.put_ingress(tunnel, parse_wildcard_domain("*.dashen.wang"))

    create_data = opener.requests[0].data
    ingress_data = opener.requests[1].data
    assert isinstance(create_data, bytes)
    assert isinstance(ingress_data, bytes)
    create_payload = json.loads(create_data)
    ingress_payload = json.loads(ingress_data)
    assert create_payload == {"name": "bt-cf-dashen-wang", "config_src": "cloudflare"}
    assert ingress_payload["config"]["ingress"] == [
        {
            "hostname": "*.dashen.wang",
            "service": "http://127.0.0.1:80",
            "originRequest": {},
        },
        {"service": "http_status:404"},
    ]


def test_remote_status_reports_tunnel_connection_and_expected_wildcard_dns_binding() -> (
    None
):
    opener = FakeOpener(
        [
            {"success": True, "result": [{"id": "connection-id"}]},
            {
                "success": True,
                "result": [
                    {
                        "id": "record-id",
                        "content": "tunnel-id.cfargotunnel.com",
                        "proxied": True,
                    }
                ],
            },
        ]
    )
    client = CloudflareClient("secret-token", opener)
    tunnel = client.tunnel_from_values("tunnel-id", "bt-cf-dashen-wang", "account-id")

    status = client.get_remote_status(
        tunnel, "zone-id", parse_wildcard_domain("*.dev.dashen.wang")
    )

    assert status.tunnel_connected is True
    assert status.dns_bound is True
