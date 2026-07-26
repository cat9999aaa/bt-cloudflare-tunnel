from __future__ import annotations

import json
import stat
from pathlib import Path

from cf_tunnel.domain import PluginConfig, parse_wildcard_domain
from cf_tunnel.storage import ConfigStore


def test_store_writes_private_configuration_without_returning_plaintext(
    tmp_path: Path,
) -> None:
    location = tmp_path / "cf_tunnel.json"
    store = ConfigStore(location)
    config = PluginConfig(
        token="token-that-must-not-be-returned",
        wildcard=parse_wildcard_domain("*.dashen.wang"),
    )

    store.save(config)

    assert stat.S_IMODE(location.stat().st_mode) == 0o600
    assert store.load() == config
    assert json.loads(location.read_text(encoding="utf-8"))["token"] == config.token
