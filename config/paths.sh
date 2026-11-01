#!/usr/bin/env bash
# shellcheck disable=SC2034
# Fuente única de rutas persistentes y temporales de Xray Manager.
# Cargar después de config/manager.conf y antes de los módulos.
: "${APP_ROOT:=/opt/xray-manager}"

readonly XRAY_MANAGER_APP_DIR="$APP_ROOT"
: "${XRAY_BIN_PATH:=/usr/local/bin/xray}"
: "${XRAY_DATA_DIR:=/usr/local/share/xray}"
XRAY_ADMIN_BIN="$XRAY_BIN_PATH"
XRAY_ADMIN_DATA="$XRAY_DATA_DIR"
readonly XRAY_MANAGER_CONFIG_DIR="/etc/xray-manager"
: "${XRAY_CONFIG_DIR:=/etc/xray}"
: "${XRAY_CONFIG_FILE:=$XRAY_CONFIG_DIR/config.json}"

readonly XRAY_MANAGER_DATA_DIR="/var/lib/xray-manager"
readonly XRAY_MANAGER_USERS_DIR="/var/lib/xray-manager/users"
readonly XRAY_MANAGER_USERS_FILE="/var/lib/xray-manager/users/users.json"
readonly XRAY_MANAGER_CONNECTIONS_DIR="/var/lib/xray-manager/connections"
readonly XRAY_MANAGER_CONNECTIONS_FILE="/var/lib/xray-manager/connections/connections.json"
readonly XRAY_MANAGER_PROFILES_DIR="/var/lib/xray-manager/profiles"
readonly XRAY_MANAGER_DOMAINS_DIR="/var/lib/xray-manager/domains"
readonly XRAY_MANAGER_CERTIFICATES_DIR="/var/lib/xray-manager/certificates"
readonly XRAY_MANAGER_HISTORY_DIR="/var/lib/xray-manager/history"
readonly XRAY_MANAGER_STATE_DIR="/var/lib/xray-manager/state"
readonly XRAY_MANAGER_LOG_DIR="/var/log/xray-manager"
readonly XRAY_MANAGER_CACHE_DIR="/var/cache/xray-manager"
: "${XRAY_MANAGER_BACKUP_DIR:=/var/backups/xray-manager}"

readonly XRAY_MANAGER_RUNTIME_DIR="/run/xray-manager"
readonly XRAY_MANAGER_INTEGRITY_LOCK="/run/xray-manager/integrity.lock"
# Alias de compatibilidad: ambos registros comparten el mismo bloqueo.
readonly XRAY_MANAGER_CONNECTIONS_LOCK="$XRAY_MANAGER_INTEGRITY_LOCK"
readonly XRAY_MANAGER_USERS_LOCK="$XRAY_MANAGER_INTEGRITY_LOCK"
readonly XRAY_MANAGER_UNINSTALL_LOCK="/run/lock/xray-manager-uninstall.lock"
