from __future__ import annotations

import json
from pathlib import Path


def test_manifest_enables_homepage_display_by_default() -> None:
    manifest = json.loads(Path("cf_tunnel/info.json").read_text(encoding="utf-8"))

    assert manifest["display"] == 1
    assert manifest["default"] is True
    assert manifest["name"] == "cf_tunnel"
