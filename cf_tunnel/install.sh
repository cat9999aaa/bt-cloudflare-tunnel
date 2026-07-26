#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="/www/server/panel/plugin/cf_tunnel"
ICON_SOURCE="$PLUGIN_DIR/icon.png"
ICON_TARGET="/www/server/panel/BTPanel/static/img/soft_ico/ico-cf_tunnel.png"

install_plugin() {
  if [ -f "$ICON_SOURCE" ]; then
    install -D -m 0644 "$ICON_SOURCE" "$ICON_TARGET"
  fi
  printf '%s\n' 'Cloudflare Tunnel 开发助手已安装。请打开设置页完成一键配置。'
}

uninstall_plugin() {
  rm -f -- "$ICON_TARGET"
  printf '%s\n' '插件已卸载。本机 cloudflared 服务和 Cloudflare Tunnel/DNS 资源不会被自动删除。'
}

case "${1:-}" in
  install) install_plugin ;;
  uninstall) uninstall_plugin ;;
  *) printf '%s\n' 'Usage: install.sh {install|uninstall}' >&2; exit 1 ;;
esac
