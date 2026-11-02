#!/usr/bin/env bash
# Preparación de identidad y unidad systemd de Xray-core.
# Este módulo nunca habilita ni inicia el servicio.

XRAY_SERVICE_USER="${XRAY_SERVICE_USER:-xray}"
XRAY_SERVICE_GROUP="${XRAY_SERVICE_GROUP:-xray}"
XRAY_SERVICE_ROOT="${XRAY_SERVICE_ROOT:-/}"
XRAY_SERVICE_UNIT_NAME="${XRAY_SERVICE_UNIT_NAME:-xray.service}"

xray_service_path() {
    local path="$1"
    if [[ "$XRAY_SERVICE_ROOT" == "/" ]]; then
        printf '%s' "$path"
    else
        printf '%s%s' "${XRAY_SERVICE_ROOT%/}" "$path"
    fi
}

xray_service_fail() {
    printf 'ERROR: %s\n' "$*" >&2
    return 1
}

xray_service_check_path_components() {
    local value="$1" current="" segment
    local -a parts=()
    IFS='/' read -r -a parts <<<"${value#/}"
    for segment in "${parts[@]}"; do
        [[ -n "$segment" ]] || continue
        current+="/$segment"
        if [[ -L "$current" ]]; then
            xray_service_fail "se detectó un componente simbólico: $current"
            return 1
        fi
    done
}

xray_service_ensure_account() {
    local group_entry passwd_entry primary_group shell home uid gid
    command -v getent >/dev/null 2>&1 || {
        xray_service_fail "falta getent"
        return 1
    }
    command -v groupadd >/dev/null 2>&1 || {
        xray_service_fail "falta groupadd"
        return 1
    }
    command -v useradd >/dev/null 2>&1 || {
        xray_service_fail "falta useradd"
        return 1
    }
    command -v id >/dev/null 2>&1 || {
        xray_service_fail "falta id"
        return 1
    }

    group_entry="$(getent group "$XRAY_SERVICE_GROUP" || true)"
    if [[ -z "$group_entry" ]]; then
        groupadd --system "$XRAY_SERVICE_GROUP" || {
            xray_service_fail "no se pudo crear el grupo $XRAY_SERVICE_GROUP"
            return 1
        }
    else
        gid="$(cut -d: -f3 <<<"$group_entry")"
        [[ "$gid" =~ ^[0-9]+$ && "$gid" -lt 1000 ]] || {
            xray_service_fail "el grupo existente $XRAY_SERVICE_GROUP no parece ser un grupo de sistema"
            return 1
        }
    fi

    passwd_entry="$(getent passwd "$XRAY_SERVICE_USER" || true)"
    if [[ -z "$passwd_entry" ]]; then
        useradd --system --gid "$XRAY_SERVICE_GROUP" --home-dir /var/lib/xray \
            --shell /usr/sbin/nologin --no-create-home "$XRAY_SERVICE_USER" ||
            {
                xray_service_fail "no se pudo crear el usuario $XRAY_SERVICE_USER"
                return 1
            }
    else
        primary_group="$(id -gn "$XRAY_SERVICE_USER" 2>/dev/null || true)"
        uid="$(id -u "$XRAY_SERVICE_USER" 2>/dev/null || true)"
        home="$(cut -d: -f6 <<<"$passwd_entry")"
        shell="$(cut -d: -f7 <<<"$passwd_entry")"
        [[ "$primary_group" == "$XRAY_SERVICE_GROUP" ]] ||
            {
                xray_service_fail "el usuario existente $XRAY_SERVICE_USER no tiene el grupo primario esperado"
                return 1
            }
        [[ "$home" == /var/lib/xray && "$shell" == /usr/sbin/nologin ]] ||
            {
                xray_service_fail "la cuenta existente $XRAY_SERVICE_USER tiene home o shell inesperados"
                return 1
            }
        [[ "$uid" =~ ^[0-9]+$ && "$uid" -lt 1000 ]] ||
            {
                xray_service_fail "la cuenta existente $XRAY_SERVICE_USER no parece ser una cuenta de sistema"
                return 1
            }
    fi
}

xray_service_unit_content() {
    cat <<'UNIT'
[Unit]
Description=Xray-core Service
Documentation=https://github.com/XTLS/Xray-core
ConditionPathExists=/etc/xray/config.json
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
User=xray
Group=xray
WorkingDirectory=/var/lib/xray
ExecStartPre=/usr/local/bin/xray run -test -config /etc/xray/config.json
ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json
Restart=on-failure
RestartSec=5s
TimeoutStopSec=30s
KillMode=mixed
UMask=0027
LimitNOFILE=1048576
StateDirectory=xray
StateDirectoryMode=0750
RuntimeDirectory=xray
RuntimeDirectoryMode=0750
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectHome=true
ProtectSystem=strict
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
ProtectClock=true
ProtectHostname=true
ProtectKernelLogs=true
LockPersonality=true
RestrictSUIDSGID=true
RestrictRealtime=true
RestrictNamespaces=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
SystemCallArchitectures=native
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
UNIT
}

xray_service_preflight() {
    local unit_dir unit_file existing_content path
    unit_dir="$(xray_service_path /etc/systemd/system)"
    unit_file="$unit_dir/$XRAY_SERVICE_UNIT_NAME"
    for path in "$unit_dir" "$unit_file"; do
        xray_service_check_path_components "$path" || return 1
    done

    if [[ "$XRAY_SERVICE_ROOT" == "/" ]]; then
        [[ "$EUID" -eq 0 ]] || {
            xray_service_fail "la preparación del servicio requiere root"
            return 1
        }
        command -v systemctl >/dev/null 2>&1 || {
            xray_service_fail "systemd/systemctl no está disponible"
            return 1
        }
        command -v systemd-analyze >/dev/null 2>&1 || {
            xray_service_fail "systemd-analyze no está disponible"
            return 1
        }
        if systemctl is-active --quiet "$XRAY_SERVICE_UNIT_NAME" 2>/dev/null ||
            { command -v pgrep >/dev/null 2>&1 && pgrep -x xray >/dev/null 2>&1; }; then
            xray_service_fail "Xray está activo; no se actualizará el binario mientras se ejecuta"
            return 1
        fi
    elif [[ "${XRAY_SERVICE_TEST_MODE:-0}" != 1 ]]; then
        xray_service_fail "el prefijo alternativo solo está permitido en modo de pruebas"
        return 1
    fi

    if [[ -e "$unit_file" ]]; then
        [[ -f "$unit_file" && ! -L "$unit_file" ]] || {
            xray_service_fail "la unidad existente no es un archivo regular"
            return 1
        }
        existing_content="$(cat "$unit_file")"
        [[ "$existing_content" == "$(xray_service_unit_content)" ]] || {
            xray_service_fail "ya existe una unidad $XRAY_SERVICE_UNIT_NAME diferente; no se sobrescribirá"
            return 1
        }
    fi
}

xray_service_prepare() {
    local binary config_dir config_file data_dir state_dir unit_dir unit_file
    local tmp_unit existing_content path unit_created=0 service_group="$XRAY_SERVICE_GROUP"

    xray_service_preflight || return 1
    binary="${XRAY_ADMIN_BIN:-${XRAY_BIN_PATH:-/usr/local/bin/xray}}"
    config_dir="${XRAY_CONFIG_DIR:-/etc/xray}"
    config_file="${XRAY_CONFIG_FILE:-$config_dir/config.json}"
    data_dir="${XRAY_ADMIN_DATA:-${XRAY_DATA_DIR:-/usr/local/share/xray}}"
    state_dir="$(xray_service_path /var/lib/xray)"
    unit_dir="$(xray_service_path /etc/systemd/system)"
    unit_file="$unit_dir/$XRAY_SERVICE_UNIT_NAME"

    [[ -x "$(xray_service_path "$binary")" ]] ||
        {
            xray_service_fail "no se encuentra el binario ejecutable de Xray-core: $(xray_service_path "$binary")"
            return 1
        }
    [[ -d "$(xray_service_path "$data_dir")" ]] ||
        {
            xray_service_fail "no existe el directorio geodata: $(xray_service_path "$data_dir")"
            return 1
        }

    for path in "$state_dir" "$(xray_service_path "$config_dir")" "$(xray_service_path "$config_file")" "$unit_dir" "$unit_file" \
        "$(xray_service_path "$binary")" "$(xray_service_path "$data_dir")" \
        "$(xray_service_path "$data_dir/geoip.dat")" "$(xray_service_path "$data_dir/geosite.dat")"; do
        xray_service_check_path_components "$path" || return 1
    done

    if [[ "$XRAY_SERVICE_ROOT" == "/" ]]; then
        [[ "$EUID" -eq 0 ]] || {
            xray_service_fail "la preparación del servicio requiere root"
            return 1
        }
        command -v systemctl >/dev/null 2>&1 || {
            xray_service_fail "systemd/systemctl no está disponible"
            return 1
        }
        command -v systemd-analyze >/dev/null 2>&1 || {
            xray_service_fail "systemd-analyze no está disponible"
            return 1
        }
        xray_service_ensure_account || return 1
    elif [[ "${XRAY_SERVICE_TEST_MODE:-0}" != 1 ]]; then
        xray_service_fail "el prefijo alternativo solo está permitido en modo de pruebas"
        return 1
    fi

    local service_owner=root service_group="$XRAY_SERVICE_GROUP"
    if [[ "$XRAY_SERVICE_ROOT" != "/" ]]; then
        service_group=root
    fi
    install -d -o root -g "$service_group" -m 750 "$(xray_service_path "$config_dir")" ||
        {
            xray_service_fail "no se pudo preparar el directorio de configuración"
            return 1
        }
    install -d -o "$service_owner" -g "$service_group" -m 750 "$state_dir" ||
        {
            xray_service_fail "no se pudo preparar el directorio de estado"
            return 1
        }

    if [[ -e "$(xray_service_path "$config_file")" || -L "$(xray_service_path "$config_file")" ]]; then
        [[ -f "$(xray_service_path "$config_file")" && ! -L "$(xray_service_path "$config_file")" ]] ||
            {
                xray_service_fail "la configuración existente no es un archivo regular"
                return 1
            }
        chown root:"$service_group" "$(xray_service_path "$config_file")" ||
            {
                xray_service_fail "no se pudo ajustar el grupo de la configuración"
                return 1
            }
        chmod 640 "$(xray_service_path "$config_file")" ||
            {
                xray_service_fail "no se pudieron ajustar los permisos de la configuración"
                return 1
            }
        if [[ "$XRAY_SERVICE_ROOT" == "/" ]] && command -v runuser >/dev/null 2>&1; then
            runuser -u "$XRAY_SERVICE_USER" -- "$(xray_service_path "$binary")" run -test -config "$(xray_service_path "$config_file")" ||
                {
                    xray_service_fail "la configuración existente no supera la validación como usuario del servicio"
                    return 1
                }
        else
            "$(xray_service_path "$binary")" run -test -config "$(xray_service_path "$config_file")" ||
                {
                    xray_service_fail "la configuración existente no supera la validación de Xray-core"
                    return 1
                }
        fi
    fi

    install -d -o root -g root -m 755 "$unit_dir" ||
        {
            xray_service_fail "no se pudo preparar el directorio systemd"
            return 1
        }
    tmp_unit="$(mktemp "$unit_dir/.${XRAY_SERVICE_UNIT_NAME}.XXXXXX")" || return 1
    xray_service_unit_content >"$tmp_unit"
    chmod 644 "$tmp_unit"
    chown root:root "$tmp_unit"

    if [[ -e "$unit_file" ]]; then
        [[ -f "$unit_file" && ! -L "$unit_file" ]] || {
            rm -f -- "$tmp_unit"
            xray_service_fail "la unidad existente no es un archivo regular"
            return 1
        }
        existing_content="$(cat "$unit_file")"
        if [[ "$existing_content" != "$(cat "$tmp_unit")" ]]; then
            rm -f -- "$tmp_unit"
            xray_service_fail "ya existe una unidad $XRAY_SERVICE_UNIT_NAME diferente; no se sobrescribirá"
            return 1
        fi
        rm -f -- "$tmp_unit"
        chown root:root "$unit_file" || {
            xray_service_fail "no se pudo asegurar la propiedad de la unidad"
            return 1
        }
        chmod 644 "$unit_file" || {
            xray_service_fail "no se pudieron asegurar los permisos de la unidad"
            return 1
        }
    else
        mv -- "$tmp_unit" "$unit_file" || {
            xray_service_fail "no se pudo instalar la unidad systemd"
            return 1
        }
        unit_created=1
    fi

    if [[ "$XRAY_SERVICE_ROOT" == "/" ]]; then
        if ! systemd-analyze verify "$unit_file"; then
            ((unit_created == 0)) || rm -f -- "$unit_file"
            xray_service_fail "systemd-analyze rechazó la unidad instalada"
            return 1
        fi
        if ! systemctl daemon-reload; then
            if ((unit_created)); then
                rm -f -- "$unit_file"
                systemctl daemon-reload >/dev/null 2>&1 || true
            fi
            xray_service_fail "systemd no pudo recargar las unidades"
            return 1
        fi
        if systemctl is-active --quiet "$XRAY_SERVICE_UNIT_NAME"; then
            xray_service_fail "el servicio ya estaba activo; el instalador no lo detendrá"
            return 1
        fi
        if systemctl is-enabled --quiet "$XRAY_SERVICE_UNIT_NAME" 2>/dev/null; then
            printf 'AVISO: la unidad ya estaba habilitada; no se modificó ese estado.\n' >&2
        fi
    fi

    printf 'Unidad %s preparada. El servicio permanece detenido y no se habilitó.\n' "$XRAY_SERVICE_UNIT_NAME"
}