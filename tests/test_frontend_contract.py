from __future__ import annotations

import re
from pathlib import Path


def test_settings_page_exposes_saved_settings_status_and_security_actions() -> None:
    html = Path("cf_tunnel/index.html").read_text(encoding="utf-8")

    assert '<meta charset="utf-8">' in html
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    assert html.count('id="cf-tunnel-domain"') == 1
    assert html.count('id="cf-tunnel-account-id"') == 1
    assert html.count('id="cf-tunnel-token"') == 1
    assert 'id="cf-tunnel-dns-binding"' in html
    assert 'placeholder="例如 *.dev.dashen.wang"' in html
    assert "支持 *.dev.dashen.wang、*.dashen.wang" in html
    assert 'id="cf-tunnel-save"' in html
    assert 'id="cf-tunnel-configure"' in html
    assert (
        'id="cf-tunnel-configure" class="cf-tunnel__button cf-tunnel__button--primary" type="button" disabled'
        in html
    )
    assert "保存设置" in html
    assert "一键安装并配置" in html
    assert "安全防护" in html
    assert "cf-tunnel-setup" in html
    assert "cf-tunnel-status-grid" in html
    assert "cf-tunnel-feedback" in html
    assert "Cloudflare Tunnel" in html
    assert "DNS 绑定" in html


def test_settings_page_shows_the_installed_plugin_version() -> None:
    html = Path("cf_tunnel/index.html").read_text(encoding="utf-8")

    assert 'id="cf-tunnel-plugin-version"' in html
    assert "插件版本 0.1.2" in html


def test_settings_page_uses_unique_dom_ids() -> None:
    html = Path("cf_tunnel/index.html").read_text(encoding="utf-8")
    identifiers = re.findall(r'\bid="([^"]+)"', html)

    assert len(identifiers) == len(set(identifiers))


def test_frontend_calls_only_plugin_status_save_configuration_and_restart_endpoints() -> (
    None
):
    script = Path("cf_tunnel/static/cf-tunnel.js").read_text(encoding="utf-8")

    assert "get_status" in script
    assert "save_settings" in script
    assert "configure" in script
    assert "restart_service" in script
    assert "tunnel_connected" in script
    assert "dns_bound" in script
    assert "restoreSubmit" in script
    assert "onError" in script
    assert "$.ajax" in script
    assert 'url: "/plugin?action=a&s=" + action + "&name=" + pluginName' in script
    assert "window.request_plugin" not in script
    assert "savedSettings" in script
    assert ".text(" in script
    assert ".html(" not in script


def test_frontend_distinguishes_a_backend_failure_from_a_disconnected_panel() -> None:
    script = Path("cf_tunnel/static/cf-tunnel.js").read_text(encoding="utf-8")

    assert "error: function ()" in script
    assert "状态读取失败，请刷新后重试；若持续失败，请查看宝塔插件日志。" in script
    assert "HTTP " not in script
    assert "无法连接宝塔插件接口" not in script


def test_frontend_marks_remote_tunnel_as_pending_before_settings_are_saved() -> None:
    script = Path("cf_tunnel/static/cf-tunnel.js").read_text(encoding="utf-8")

    assert 'settingsSaved ? (tunnelConnected ? "已连接" : "未连接") : "待配置"' in script


def test_frontend_uses_design_tokens_and_reduced_motion_support() -> None:
    stylesheet = Path("cf_tunnel/static/cf-tunnel.css").read_text(encoding="utf-8")

    assert "--cf-primary" in stylesheet
    assert "--cf-warning-border" in stylesheet
    assert "prefers-reduced-motion" in stylesheet
    assert "cf-tunnel__layout" in stylesheet
    assert "@media (max-width: 420px)" in stylesheet
    assert "min-block-size: 44px;" in stylesheet
