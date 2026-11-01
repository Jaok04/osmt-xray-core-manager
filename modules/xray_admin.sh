#!/usr/bin/env bash
# Gestión controlada de Xray-core. Solo instala el binario y geodata;
# no crea/edita unidades systemd, no modifica configuraciones y no inicia servicios.

XRAY_ADMIN_RELEASE_API="https://api.github.com/repos/XTLS/Xray-core/releases/tags"
XRAY_ADMIN_RELEASE_BASE="https://github.com/XTLS/Xray-core/releases/download"
XRAY_ADMIN_BIN="/usr/local/bin/xray"
XRAY_ADMIN_DATA="/usr/local/share/xray"
XRAY_ADMIN_CACHE="${XRAY_MANAGER_CACHE_DIR:-/var/cache/xray-manager}/releases"
XRAY_ADMIN_BACKUPS="${XRAY_MANAGER_BACKUP_DIR:-/var/backups/xray-manager}/xray-core"
XRAY_ADMIN_LOCK="/run/lock/xray-manager-xray-admin.lock"

xray_admin_require_root() {
	if [[ "${EUID}" -ne 0 ]]; then
		printf 'Esta operación requiere root. El administrador no intenta autoelevarse.\n' >&2
		return 1
	fi
}

xray_admin_require_tools() {
	local missing=0 tool
	for tool in curl jq python3 sha256sum flock install; do
		if ! command -v "$tool" >/dev/null 2>&1; then
			printf 'Falta la dependencia requerida: %s\n' "$tool" >&2
			missing=1
		fi
	done
	return "$missing"
}

xray_admin_compatible_versions() {
	# Solo se exponen versiones con adaptador y prueba de configuración.
	if [[ -n "${XRAY_VERSION:-}" && -f "$APP_ROOT/modules/vless_xray_${XRAY_VERSION//./_}.sh" ]]; then
		printf '%s\n' "$XRAY_VERSION"
	fi
}

xray_admin_asset_arch() {
	case "$(uname -m)" in
	x86_64 | amd64) printf '%s' '64' ;;
	aarch64 | arm64) printf '%s' 'arm64-v8a' ;;
	armv7l | armv7) printf '%s' 'arm32-v7a' ;;
	i386 | i486 | i586 | i686) printf '%s' '32' ;;
	*) return 1 ;;
	esac
}

xray_admin_release_asset_name() {
	local arch
	arch="$(xray_admin_asset_arch)" || {
		printf 'Arquitectura no soportada por el catálogo: %s\n' "$(uname -m)" >&2
		return 1
	}
	printf 'Xray-linux-%s.zip' "$arch"
}

xray_admin_lock() {
	install -d -m 700 /run/lock
	exec {XRAY_ADMIN_LOCK_FD}>"$XRAY_ADMIN_LOCK"
	flock -n "$XRAY_ADMIN_LOCK_FD" || {
		printf 'Ya hay otra operación de administración de Xray-core en curso.\n' >&2
		return 1
	}
}

xray_admin_latest_release() {
	local response tag
	command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 || return 1
	response="$(curl --fail --silent --show-error --location --connect-timeout 8 --max-time 20 \
		https://api.github.com/repos/XTLS/Xray-core/releases/latest)" || return 1
	jq -e '.draft == false and .prerelease == false and (.tag_name | type == "string")' \
		<<<"$response" >/dev/null || return 1
	tag="$(jq -r '.tag_name' <<<"$response")"
	[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
	printf '%s\n' "${tag#v}"
}

xray_admin_show_versions() {
	local version
	ui_clear
	ui_title "VERSIONES COMPATIBLES DE XRAY-CORE"
	printf 'Las versiones mostradas cuentan con adaptador local y validación de configuración.\n\n'
	while IFS= read -r version; do
		[[ -n "$version" ]] && printf '  [1] Xray-core %s (adaptador validado)\n' "$version"
	done < <(xray_admin_compatible_versions)
	printf '\nNo se ofrecen versiones que todavía no tengan adaptador y pruebas aprobadas.\n'
	ui_pause
}

xray_admin_fetch_verified_release() {
	local version="$1" workdir="$2" asset api_json digest_file expected actual asset_name
	[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
		printf 'Formato de versión inválido.\n' >&2
		return 1
	}
	asset_name="$(xray_admin_release_asset_name)" || return 1
	asset="${asset_name}"
	api_json="$workdir/release.json"
	digest_file="$workdir/$asset.dgst"

	curl --fail --silent --show-error --location --connect-timeout 10 --max-time 30 \
		"$XRAY_ADMIN_RELEASE_API/v$version" -o "$api_json" || {
		printf 'No se pudo consultar el release oficial v%s.\n' "$version" >&2
		return 1
	}
	jq -e --arg tag "v$version" --arg asset "$asset" '
        .tag_name == $tag and .draft == false and .prerelease == false and
        ([.assets[].name] | index($asset) != null) and
        ([.assets[].name] | index($asset + ".dgst") != null)
    ' "$api_json" >/dev/null || {
		printf 'Release o archivos oficiales no coinciden con v%s.\n' "$version" >&2
		return 1
	}

	curl --fail --silent --show-error --location --connect-timeout 10 --max-time 180 \
		"$XRAY_ADMIN_RELEASE_BASE/v$version/$asset" -o "$workdir/$asset" || return 1
	curl --fail --silent --show-error --location --connect-timeout 10 --max-time 30 \
		"$XRAY_ADMIN_RELEASE_BASE/v$version/$asset.dgst" -o "$digest_file" || return 1

	expected="$(awk -F= '/^SHA2-256=/ {gsub(/[[:space:]]/, "", $2); print tolower($2)}' "$digest_file")"
	[[ "$expected" =~ ^[a-f0-9]{64}$ ]] || {
		printf 'El release no proporcionó un SHA2-256 válido.\n' >&2
		return 1
	}
	actual="$(sha256sum "$workdir/$asset" | awk '{print tolower($1)}')"
	if [[ "$version" == "${XRAY_VERSION:-}" && "$(xray_admin_asset_arch)" == '64' && -n "${XRAY_LINUX_AMD64_SHA256:-}" ]]; then
		[[ "$expected" == "${XRAY_LINUX_AMD64_SHA256,,}" ]] || {
			printf 'El SHA-256 publicado no coincide con el valor fijado en la configuración.\n' >&2
			return 1
		}
	fi
	[[ "$actual" == "$expected" ]] || {
		printf 'ERROR: SHA-256 no coincide. Se descarta el paquete.\n' >&2
		return 1
	}
	printf '%s\n' "$actual" >"$workdir/package.sha256"
	chmod 600 "$workdir/package.sha256"
}

xray_admin_extract_stage() {
	local version="$1" workdir="$2" stage="$3" archive
	archive="$workdir/$(xray_admin_release_asset_name)" || return 1
	install -d -m 700 "$stage"
	python3 - "$archive" "$stage" <<'PY'
import os, sys, zipfile
archive, destination = sys.argv[1:3]
allowed = {"xray", "geoip.dat", "geosite.dat", "LICENSE", "README.md"}
with zipfile.ZipFile(archive) as zf:
    names = set(zf.namelist())
    if not {"xray", "geoip.dat", "geosite.dat"}.issubset(names):
        raise SystemExit("El paquete no contiene xray, geoip.dat y geosite.dat.")
    for info in zf.infolist():
        name = info.filename
        if name not in allowed or "/" in name or "\\" in name or info.is_dir():
            continue
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise SystemExit("El paquete contiene un enlace simbólico no permitido.")
        target = os.path.join(destination, name)
        with zf.open(info) as src, open(target, "wb") as dst:
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)
        os.chmod(target, 0o700 if name == "xray" else 0o644)
PY
	"$stage/xray" version | grep -F "Xray $version " >/dev/null || {
		printf 'El binario descargado no declara la versión solicitada.\n' >&2
		return 1
	}
	"$stage/xray" version | head -n 1
}

xray_admin_backup_existing() {
	local backup_dir="$1" found=0
	install -d -m 700 "$backup_dir"
	if [[ -e "$XRAY_ADMIN_BIN" ]]; then
		cp -a "$XRAY_ADMIN_BIN" "$backup_dir/xray"
		found=1
	fi
	for file in geoip.dat geosite.dat; do
		if [[ -e "$XRAY_ADMIN_DATA/$file" ]]; then
			cp -a "$XRAY_ADMIN_DATA/$file" "$backup_dir/$file"
			found=1
		fi
	done
	if ((found)); then
		printf 'Respaldo de binario/geodata: %s\n' "$backup_dir"
	else
		rmdir "$backup_dir"
		printf '%s\n' 'No había binario ni geodata previos que respaldar.'
	fi
}

xray_admin_install_version() {
	local version="$1" mode="$2" workdir stage backup_dir backup_created=0
	xray_admin_require_root && xray_admin_require_tools && xray_admin_lock || return 1
	case " $(xray_admin_compatible_versions | tr '\n' ' ') " in
	*" $version "*) ;;
	*)
		printf 'La versión %s no está habilitada: falta adaptador compatible validado.\n' "$version" >&2
		return 1
		;;
	esac
	case "$mode" in install | update | reinstall | repair) ;; *) return 2 ;; esac

	if [[ -x "$XRAY_ADMIN_BIN" ]]; then
		case "$mode" in
		install)
			printf 'Xray-core ya existe. Usa actualizar o reinstalar.\n' >&2
			return 1
			;;
		update)
			local installed
			installed="$("$XRAY_ADMIN_BIN" version 2>/dev/null | head -n 1 || true)"
			if [[ "$installed" == *"Xray $version "* ]]; then
				printf 'La versión %s ya está instalada.\n' "$version"
				return 0
			fi
			;;
		reinstall | repair) ;;
		esac
	elif [[ "$mode" == update || "$mode" == reinstall ]]; then
		printf 'No hay una instalación que actualizar o reinstalar.\n' >&2
		return 1
	fi

	workdir="$(mktemp -d "$XRAY_ADMIN_CACHE.XXXXXX")" || return 1
	stage="$workdir/stage"
	backup_dir="$XRAY_ADMIN_BACKUPS/$(date -u +%Y%m%dT%H%M%SZ)"
	local committed=0
	# shellcheck disable=SC2317
	xray_admin_cleanup() {
		if ((committed == 0)); then
			if [[ -x "$backup_dir/xray" ]]; then
				install -m 755 "$backup_dir/xray" "$XRAY_ADMIN_BIN.rollback"
				mv -f "$XRAY_ADMIN_BIN.rollback" "$XRAY_ADMIN_BIN"
			else
				rm -f -- "$XRAY_ADMIN_BIN.new" "$XRAY_ADMIN_BIN"
			fi
			for file in geoip.dat geosite.dat; do
				if [[ -f "$backup_dir/$file" ]]; then
					install -d -m 755 "$XRAY_ADMIN_DATA"
					install -m 644 "$backup_dir/$file" "$XRAY_ADMIN_DATA/$file.rollback"
					mv -f "$XRAY_ADMIN_DATA/$file.rollback" "$XRAY_ADMIN_DATA/$file"
				else
					rm -f -- "$XRAY_ADMIN_DATA/$file.new" "$XRAY_ADMIN_DATA/$file"
				fi
			done
		fi
		rm -rf -- "$workdir"
	}
	trap xray_admin_cleanup RETURN

	printf 'Consultando release oficial y verificando SHA-256 de Xray-core %s...\n' "$version"
	xray_admin_fetch_verified_release "$version" "$workdir" || return 1
	xray_admin_extract_stage "$version" "$workdir" "$stage" || return 1

	install -d -m 755 "$(dirname "$XRAY_ADMIN_BIN")" "$XRAY_ADMIN_DATA" "$XRAY_ADMIN_BACKUPS"
	xray_admin_backup_existing "$backup_dir" || return 1
	[[ -d "$backup_dir" ]] && backup_created=1

	install -m 755 "$stage/xray" "$XRAY_ADMIN_BIN.new"
	install -m 644 "$stage/geoip.dat" "$XRAY_ADMIN_DATA/geoip.dat.new"
	install -m 644 "$stage/geosite.dat" "$XRAY_ADMIN_DATA/geosite.dat.new"
	"$XRAY_ADMIN_BIN.new" version | grep -F "Xray $version " >/dev/null || return 1
	mv -f "$XRAY_ADMIN_BIN.new" "$XRAY_ADMIN_BIN"
	mv -f "$XRAY_ADMIN_DATA/geoip.dat.new" "$XRAY_ADMIN_DATA/geoip.dat"
	mv -f "$XRAY_ADMIN_DATA/geosite.dat.new" "$XRAY_ADMIN_DATA/geosite.dat"
	chown root:root "$XRAY_ADMIN_BIN" "$XRAY_ADMIN_DATA/geoip.dat" "$XRAY_ADMIN_DATA/geosite.dat"
	chmod 755 "$XRAY_ADMIN_BIN"
	chmod 644 "$XRAY_ADMIN_DATA/geoip.dat" "$XRAY_ADMIN_DATA/geosite.dat"
	"$XRAY_ADMIN_BIN" version | grep -F "Xray $version " >/dev/null || return 1
	committed=1
	printf '\nXray-core %s quedó instalado y verificado.\n' "$version"
	printf 'No se creó ni reinició ningún servicio systemd.\n'
	((backup_created)) && printf 'Respaldo previo conservado en: %s\n' "$backup_dir"
	trap - RETURN
	rm -rf -- "$workdir"
}

xray_admin_install_menu_action() {
	local mode="$1" version choice
	ui_clear
	ui_title "SELECCIÓN DE VERSIÓN COMPATIBLE"
	printf 'Versiones disponibles con adaptador validado:\n\n'
	local versions=()
	mapfile -t versions < <(xray_admin_compatible_versions)
	if (("${#versions[@]}" == 0)); then
		printf 'No hay versiones compatibles habilitadas.\n'
		ui_pause
		return 1
	fi
	local i=1
	for version in "${versions[@]}"; do
		printf '  [%s] Xray-core %s\n' "$i" "$version"
		((i += 1))
	done
	printf '  [0] Volver\n\n'
	ui_read_option "Selecciona la versión: " choice
	[[ "$choice" =~ ^[0-9]+$ ]] || {
		printf 'Selección no válida.\n'
		ui_pause
		return 1
	}
	((choice == 0)) && return 0
	((choice >= 1 && choice <= ${#versions[@]})) || {
		printf 'Selección fuera de rango.\n'
		ui_pause
		return 1
	}
	version="${versions[choice - 1]}"
	printf '\nOperación: %s\nVersión: %s\n' "$mode" "$version"
	printf 'Se reemplazarán únicamente el binario y los archivos geoip/geosite.\n'
	printf 'Configuración, certificados, servicio systemd y datos del administrador no se modificarán.\n'
	if ui_confirm "¿Confirmas ejecutar esta operación en el VPS?"; then
		xray_admin_install_version "$version" "$mode"
	else
		printf 'Operación cancelada.\n'
	fi
	ui_pause
}