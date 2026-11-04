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
readonly XRAY_MANAGER_KEYS_DIR="/etc/xray-manager/keys"
readonly XRAY_MANAGER_MASTER_KEY_FILE="/etc/xray-manager/keys/master.key"
: "${XRAY_CONFIG_DIR:=/etc/xray}"
: "${XRAY_CONFIG_FILE:=$XRAY_CONFIG_DIR/config.json}"

readonly XRAY_MANAGER_DATA_DIR="/var/lib/xray-manager"
readonly XRAY_MANAGER_USERS_DIR="/var/lib/xray-manager/users"
readonly XRAY_MANAGER_USERS_FILE="/var/lib/xray-manager/users/users.json"
readonly XRAY_MANAGER_CONNECTIONS_DIR="/var/lib/xray-manager/connections"
readonly XRAY_MANAGER_VMESS_DIR="/var/lib/xray-manager/vmess"
readonly XRAY_MANAGER_VMESS_CONFIGS_DIR="/var/lib/xray-manager/vmess/configurations"
readonly XRAY_MANAGER_VMESS_SECRETS_DIR="/var/lib/xray-manager/vmess/secrets"
readonly XRAY_MANAGER_CONNECTION_CONFIGS_DIR="/var/lib/xray-manager/connections/configurations"
readonly XRAY_MANAGER_SECRETS_DIR="/var/lib/xray-manager/secrets"
readonly XRAY_MANAGER_CONNECTIONS_FILE="/var/lib/xray-manager/connections/connections.json"
readonly XRAY_MANAGER_PROFILES_DIR="/var/lib/xray-manager/profiles"
: "${XRAY_MANAGER_CONFIGURATIONS_DIR:=/var/lib/xray-manager/configurations}"
readonly XRAY_MANAGER_CONFIGURATIONS_DIR
: "${XRAY_MANAGER_VALIDATION_DIR:=/var/lib/xray-manager/validation}"
readonly XRAY_MANAGER_VALIDATION_DIR
: "${XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE:=$XRAY_MANAGER_MASTER_KEY_FILE}"
readonly XRAY_MANAGER_CONFIGURATIONS_MASTER_KEY_FILE
readonly XRAY_MANAGER_DOMAINS_DIR="/var/lib/xray-manager/domains"
readonly XRAY_MANAGER_CERTIFICATES_DIR="/var/lib/xray-manager/certificates"
readonly XRAY_MANAGER_CERTIFICATES_CATALOG_FILE="/var/lib/xray-manager/certificates/catalog.json"
readonly XRAY_MANAGER_CERTIFICATES_MANAGED_DIR="/var/lib/xray-manager/certificates/managed"
readonly XRAY_MANAGER_CERTIFICATES_REFERENCES_DIR="/var/lib/xray-manager/certificates/references"
readonly XRAY_MANAGER_CERTIFICATES_SECRETS_DIR="/var/lib/xray-manager/certificates/secrets"
readonly XRAY_MANAGER_CERTIFICATES_LOCK="/run/xray-manager-certificate-locks/catalog.lock"
readonly XRAY_MANAGER_CERTIFICATES_RUNTIME_DIR="/run/xray-manager-certificates"
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