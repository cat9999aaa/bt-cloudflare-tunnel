from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast, final

try:
    from .domain import (
        PluginConfig,
        parse_cloudflare_account_id,
        parse_wildcard_domain,
    )
except ImportError:
    from domain import PluginConfig, parse_cloudflare_account_id, parse_wildcard_domain


@final
class ConfigStore:
    """Stores the plugin configuration in a root-readable private JSON file."""

    def __init__(self, location: Path) -> None:
        self._location: Path = location

    def load(self) -> PluginConfig | None:
        if not self._location.exists():
            return None

        raw_payload = cast(
            object, json.loads(self._location.read_text(encoding="utf-8"))
        )
        if not isinstance(raw_payload, dict):
            raise TypeError("插件配置文件格式异常")
        payload = cast(dict[str, object], raw_payload)
        account_id = self._optional_string(payload, "account_id")
        return PluginConfig(
            token=str(payload["token"]),
            wildcard=parse_wildcard_domain(str(payload["wildcard_domain"])),
            zone_id=self._optional_string(payload, "zone_id"),
            account_id=(
                parse_cloudflare_account_id(account_id)
                if account_id is not None
                else None
            ),
            tunnel_id=self._optional_string(payload, "tunnel_id"),
            tunnel_name=self._optional_string(payload, "tunnel_name"),
            dns_target=self._optional_string(payload, "dns_target"),
        )

    def save(self, config: PluginConfig) -> None:
        self._location.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self._location.with_suffix(".tmp")
        _ = temporary.write_text(
            json.dumps(
                {
                    "token": config.token,
                    "wildcard_domain": config.wildcard.value,
                    "zone_id": config.zone_id,
                    "account_id": (
                        config.account_id.value
                        if config.account_id is not None
                        else None
                    ),
                    "tunnel_id": config.tunnel_id,
                    "tunnel_name": config.tunnel_name,
                    "dns_target": config.dns_target,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        _ = temporary.chmod(0o600)
        os.replace(temporary, self._location)
        _ = self._location.chmod(0o600)

    @staticmethod
    def _optional_string(payload: dict[str, object], key: str) -> str | None:
        value = payload.get(key)
        return value if isinstance(value, str) and value else None
