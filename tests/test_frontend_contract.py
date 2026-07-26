from __future__ import annotations

import re
from pathlib import Path


def test_settings_page_exposes_setup_status_and_security_actions() -> None:
    html = Path("cf_tunnel/index.html").read_text(encoding="utf-8")

    assert '<meta charset="utf-8">' in html
    assert html.count('id="cf-tunnel-domain"') == 1
    assert 'id="cf-tunnel-dns-binding"' in html
    assert 'placeholder="例如 *.dev.dashen.wang"' in html
    assert "支持 *.dev.dashen.wang、*.dashen.wang" in html
    assert "一键安装并配置" in html
    assert "安全防护" in html
    assert "cf-tunnel-setup" in html
    assert "cf-tunnel-status-grid" in html
    assert "cf-tunnel-feedback" in html
    assert "Cloudflare Tunnel" in html
    assert "DNS 绑定" in html


def test_settings_page_uses_unique_dom_ids() -> None:
    html = Path("cf_tunnel/index.html").read_text(encoding="utf-8")
    identifiers = re.findall(r'\bid="([^"]+)"', html)

    assert len(identifiers) == len(set(identifiers))


def test_frontend_calls_only_plugin_status_configuration_and_restart_endpoints() -> (
    None
):
    script = Path("cf_tunnel/static/cf-tunnel.js").read_text(encoding="utf-8")

    assert "get_status" in script
    assert "configure" in script
    assert "restart_service" in script
    assert "tunnel_connected" in script
    assert "dns_bound" in script
    assert "restoreSubmit" in script
    assert "onError" in script
    assert ".text(" in script
    assert ".html(" not in script


def test_frontend_uses_design_tokens_and_reduced_motion_support() -> None:
    stylesheet = Path("cf_tunnel/static/cf-tunnel.css").read_text(encoding="utf-8")

    assert "--cf-primary" in stylesheet
    assert "--cf-warning-border" in stylesheet
    assert "prefers-reduced-motion" in stylesheet
    assert "minmax(min(13rem, 100%), 1fr)" in stylesheet
