from __future__ import annotations

import re
from dataclasses import dataclass


class DomainValidationError(ValueError):
    """Raised when a wildcard hostname cannot be safely configured."""


@dataclass(frozen=True, slots=True)
class WildcardDomain:
    value: str
    hostname: str


@dataclass(frozen=True, slots=True)
class PluginConfig:
    token: str
    wildcard: WildcardDomain
    zone_id: str | None = None
    account_id: str | None = None
    tunnel_id: str | None = None
    tunnel_name: str | None = None
    dns_target: str | None = None


_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def parse_wildcard_domain(raw: str) -> WildcardDomain:
    value = raw.strip().lower()
    if value != raw or not value.startswith("*."):
        raise DomainValidationError("请输入 *.example.com 形式的通配域名")

    hostname = value[2:]
    labels = hostname.split(".")
    if len(labels) < 2 or any(_LABEL.fullmatch(label) is None for label in labels):
        raise DomainValidationError("请输入有效的通配 FQDN")

    return WildcardDomain(value=value, hostname=hostname)
