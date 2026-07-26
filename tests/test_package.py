from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path


def test_plugin_archive_contains_runtime_files_but_no_tests_or_secret_configuration() -> (
    None
):
    subprocess.run(
        ["bash", "package-plugin.sh"], check=True, capture_output=True, text=True
    )

    with zipfile.ZipFile(Path("dist/cf_tunnel.zip")) as archive:
        names = archive.namelist()

    assert "cf_tunnel/info.json" in names
    assert "cf_tunnel/cf_tunnel_main.py" in names
    assert "cf_tunnel/index.html" in names
    assert "cf_tunnel/icon.png" in names
    assert not any(name.startswith("tests/") for name in names)
    assert not any("config.json" in name for name in names)


def test_readme_documents_permissions_baota_usage_and_security() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "Cloudflare Tunnel" in readme
    assert "Cloudflare Tunnel:Edit" in readme
    assert "DNS:Edit" in readme
    assert "宝塔" in readme
    assert "安全防护" in readme
