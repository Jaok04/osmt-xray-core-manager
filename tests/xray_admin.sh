#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ROOT="$ROOT"
# shellcheck disable=SC1091
source "$ROOT/config/manager.conf"
# shellcheck disable=SC1091
source "$ROOT/config/xray-version.conf"
# shellcheck disable=SC1091
source "$ROOT/modules/xray_admin.sh"

mapfile -t versions < <(xray_admin_compatible_versions)
[[ "${#versions[@]}" -eq 1 ]]
[[ "${versions[0]}" == '26.10.31' ]]
[[ "$(xray_admin_release_asset_name)" == 'Xray-linux-64.zip' ]]
if xray_admin_install_version '26.9.9' install >/dev/null 2>&1; then
	echo 'ERROR: se permitió una versión sin adaptador validado.' >&2
	exit 1
fi
printf '%s\n' 'OK: catálogo de versiones compatibles, arquitectura Linux amd64 y rechazo de versiones sin adaptador.'