#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$PROJECT_DIR/dist"
STAGING_DIR="$(mktemp -d)"

cleanup() {
  rm -rf -- "$STAGING_DIR"
}
trap cleanup EXIT

mkdir -p "$OUTPUT_DIR" "$STAGING_DIR/cf_tunnel"
cp -R "$PROJECT_DIR/cf_tunnel/." "$STAGING_DIR/cf_tunnel/"
find "$STAGING_DIR/cf_tunnel" -type d -name '__pycache__' -prune -exec rm -rf -- {} +
find "$STAGING_DIR/cf_tunnel" -type f \( -name 'config.json' -o -name '*.pyc' -o -name '*.log' \) -delete

rm -f -- "$OUTPUT_DIR/cf_tunnel.zip"
(cd "$STAGING_DIR" && zip -qr "$OUTPUT_DIR/cf_tunnel.zip" cf_tunnel)
printf '已生成 %s\n' "$OUTPUT_DIR/cf_tunnel.zip"
