from __future__ import annotations

import json
import tomllib
from pathlib import Path


def test_manifest_enables_homepage_display_by_default() -> None:
    manifest = json.loads(Path("cf_tunnel/info.json").read_text(encoding="utf-8"))

    assert manifest["display"] == 1
    assert manifest["default"] is True
    assert manifest["name"] == "cf_tunnel"


def test_plugin_and_project_versions_stay_in_sync() -> None:
    manifest = json.loads(Path("cf_tunnel/info.json").read_text(encoding="utf-8"))
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert manifest["versions"] == project["project"]["version"]
