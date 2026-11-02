#!/usr/bin/env bash
# shellcheck disable=SC2016
VLESS_BACKUP_SCRIPT="${APP_ROOT:-/opt/xray-manager}/scripts/vless_backup.py"
VLESS_BACKUP_ROOT="${XRAY_MANAGER_BACKUP_DIR:-/var/backups/xray-manager}/vless"

vless_backup_menu() {
    local option backup_id backup_path output
    while true; do
        ui_clear
        ui_title "BACKUP Y RECUPERACIÓN VLESS"
        printf '\n  [1] Crear backup de datos\n  [2] Restaurar backup de datos\n  [3] Crear backup de recuperación de clave\n  [4] Recuperar clave maestra\n  [5] Ver backups disponibles\n  [6] Verificar integridad de un backup\n  [0] Volver\n\n'
        ui_read_option "Selecciona una opción: " option
        case "$option" in
        1)
            if output="$(python3 "$VLESS_BACKUP_SCRIPT" backup-data 2>&1)"; then printf '\n%s\n' "$output"; else printf '\nFalló la creación del backup:\n%s\n' "$output"; fi
            ui_pause
            ;;
        2)
            printf '\nBackups de datos disponibles:\n'
            python3 "$VLESS_BACKUP_SCRIPT" list || true
            printf '\nIntroduce el identificador exacto del backup: '
            IFS= read -r backup_id
            backup_path="$VLESS_BACKUP_ROOT/data/$backup_id"
            if [[ ! "$backup_id" =~ ^[0-9]{8}T[0-9]{6}\.[0-9]{6}Z$ ]]; then
                printf 'Identificador no válido.\n'
                ui_pause
                continue
            fi
            python3 "$VLESS_BACKUP_SCRIPT" restore-data --backup-dir "$backup_path" || true
            ui_pause
            ;;
        3)
            printf '\nBackups de datos disponibles:\n'
            python3 "$VLESS_BACKUP_SCRIPT" list || true
            printf '\nIntroduce el identificador exacto del backup asociado: '
            IFS= read -r backup_id
            if [[ ! "$backup_id" =~ ^[0-9]{8}T[0-9]{6}\.[0-9]{6}Z$ ]]; then
                printf 'Identificador no válido.\n'
                ui_pause
                continue
            fi
            python3 "$VLESS_BACKUP_SCRIPT" create-recovery --backup-dir "$VLESS_BACKUP_ROOT/data/$backup_id" || true
            ui_pause
            ;;
        4)
            printf '\nIntroduce el identificador exacto del paquete de recuperación: '
            IFS= read -r backup_id
            if [[ ! "$backup_id" =~ ^[0-9]{8}T[0-9]{6}\.[0-9]{6}Z$ ]]; then
                printf 'Identificador no válido.\n'
                ui_pause
                continue
            fi
            python3 "$VLESS_BACKUP_SCRIPT" recover-key --recovery-dir "$VLESS_BACKUP_ROOT/recovery/$backup_id" || true
            ui_pause
            ;;
        5)
            python3 "$VLESS_BACKUP_SCRIPT" list || true
            printf '\nNo se eliminan backups automáticamente. Conserva una copia externa del paquete de recuperación.\n'
            ui_pause
            ;;
        6)
            printf '\nIntroduce el identificador exacto del backup de datos: '
            IFS= read -r backup_id
            if [[ ! "$backup_id" =~ ^[0-9]{8}T[0-9]{6}\.[0-9]{6}Z$ ]]; then
                printf 'Identificador no válido.\n'
                ui_pause
                continue
            fi
            python3 "$VLESS_BACKUP_SCRIPT" verify-data --backup-dir "$VLESS_BACKUP_ROOT/data/$backup_id" || true
            ui_pause
            ;;
        0) return 0 ;;
        *)
            printf '\nOpción no válida.\n'
            ui_pause
            ;;
        esac
    done
}
