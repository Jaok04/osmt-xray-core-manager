#!/usr/bin/env bash
# Administración de Xray-core: instalación/integridad y preparación explícita del servicio.
# Las acciones de instalación no crean unidades ni inician servicios.

XRAY_ADMIN_RELEASE_API="https://api.github.com/repos/XTLS/Xray-core/releases/tags"
XRAY_ADMIN_RELEASE_BASE="https://github.com/XTLS/Xray-core/releases/download"
: "${XRAY_ADMIN_BIN:=${XRAY_BIN_PATH:-/usr/local/bin/xray}}"
: "${XRAY_ADMIN_DATA:=${XRAY_DATA_DIR:-/usr/local/share/xray}}"
: "${XRAY_ADMIN_MANIFEST:=/var/lib/xray-manager/state/xray-install.json}"
XRAY_ADMIN_CACHE="${XRAY_MANAGER_CACHE_DIR:-/var/cache/xray-manager}/releases"
XRAY_ADMIN_BACKUPS="${XRAY_MANAGER_BACKUP_DIR:-/var/backups/xray-manager}/xray-core"
XRAY_ADMIN_LOCK="${XRAY_ADMIN_LOCK:-/run/lock/xray-manager-xray-admin.lock}"
# shellcheck disable=SC1091
. "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../lib" && pwd)/operation_lock.sh"

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
	local lock_dir
	lock_dir="$(dirname "$XRAY_ADMIN_LOCK")"
	if [[ ! -d "$lock_dir" ]]; then
		install -d -o root -g root -m 700 "$lock_dir" || return 1
	fi
	if [[ ! -d "$lock_dir" || -L "$lock_dir" || -L "$XRAY_ADMIN_LOCK" || -d "$XRAY_ADMIN_LOCK" ]]; then
		printf 'La ruta del bloqueo de Xray-core no es segura.
' >&2
		return 1
	fi
	if ! exec {XRAY_ADMIN_LOCK_FD}>>"$XRAY_ADMIN_LOCK"; then
		printf 'No se pudo abrir el bloqueo de Xray-core.
' >&2
		return 1
	fi
	if ! flock -n "$XRAY_ADMIN_LOCK_FD"; then
		printf 'Ya hay otra operación de administración de Xray-core en curso.
' >&2
		exec {XRAY_ADMIN_LOCK_FD}>&-
		unset XRAY_ADMIN_LOCK_FD
		return 1
	fi
}

xray_admin_unlock() {
	if [[ "${XRAY_ADMIN_LOCK_FD:-}" =~ ^[0-9]+$ ]]; then
		flock -u "$XRAY_ADMIN_LOCK_FD" 2>/dev/null || true
		exec {XRAY_ADMIN_LOCK_FD}>&-
		unset XRAY_ADMIN_LOCK_FD
	fi
	if [[ "${XRAY_ADMIN_LIFECYCLE_FD:-}" =~ ^[0-9]+$ ]]; then
		manager_lock_release "$XRAY_ADMIN_LIFECYCLE_FD"
		unset XRAY_ADMIN_LIFECYCLE_FD
	fi
}

xray_admin_integrity_check() {
	local action="$1"
	local helper="${APP_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}/scripts/xray_install_integrity.py"
	[[ -f "$helper" && ! -L "$helper" ]] || {
		printf 'No está disponible el verificador de integridad de Xray-core.\n' >&2
		return 1
	}
	python3 "$helper" "$action" \
		--manifest "$XRAY_ADMIN_MANIFEST" \
		--binary "$XRAY_ADMIN_BIN" \
		--geoip "$XRAY_ADMIN_DATA/geoip.dat" \
		--geosite "$XRAY_ADMIN_DATA/geosite.dat" \
		--architecture "$(uname -m)" "${@:2}"
}

xray_admin_verify_installation() {
	xray_admin_integrity_check verify
}

xray_admin_record_installation() {
	local version="$1" package_sha256="$2"
	xray_admin_integrity_check record --version "$version" --package-sha256 "$package_sha256"
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
	install -d -m 700 "$stage" || return 1
	python3 - "$archive" "$stage" <<'PY' || return 1
import os, sys, zipfile
archive, destination = sys.argv[1:3]
required = {"xray", "geoip.dat", "geosite.dat"}
allowed = required | {"LICENSE", "README.md"}
max_uncompressed = 100 * 1024 * 1024
try:
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError("El ZIP contiene nombres de archivo duplicados.")
        if not required.issubset(set(names)):
            raise ValueError("El paquete no contiene xray, geoip.dat y geosite.dat.")
        if sum(info.file_size for info in infos) > max_uncompressed:
            raise ValueError("El contenido descomprimido supera el límite permitido.")
        for info in infos:
            name = info.filename
            if name not in allowed or "/" in name or '\\' in name or info.is_dir():
                raise ValueError(f"Entrada ZIP no permitida: {name!r}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode not in (0, 0o100000):
                raise ValueError(f"Tipo de archivo ZIP no permitido: {name!r}")
        bad = zf.testzip()
        if bad is not None:
            raise ValueError(f"CRC inválido en la entrada: {bad!r}")
        for info in infos:
            target = os.path.join(destination, info.filename)
            with zf.open(info) as src, open(target, "xb") as dst:
                while True:
                    block = src.read(1024 * 1024)
                    if not block:
                        break
                    dst.write(block)
            os.chmod(target, 0o700 if info.filename == "xray" else 0o644)
except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
    print(f"Extracción segura fallida: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
	"$stage/xray" version | grep -F "Xray $version " >/dev/null || {
		printf 'El binario descargado no declara la versión solicitada.
' >&2
		return 1
	}
	"$stage/xray" version | head -n 1
}

xray_admin_backup_existing() {
	local backup_dir="$1" found=0 file
	install -d -m 700 "$backup_dir" || return 1
	if [[ -L "$XRAY_ADMIN_BIN" || -L "$XRAY_ADMIN_DATA" || -L "$(dirname "$XRAY_ADMIN_BIN")" || -L "$XRAY_ADMIN_DATA/geoip.dat" || -L "$XRAY_ADMIN_DATA/geosite.dat" || -L "$XRAY_ADMIN_MANIFEST" || -L "$(dirname "$XRAY_ADMIN_MANIFEST")" ]]; then
		printf 'Se detectó un enlace simbólico en los artefactos/manifiesto de Xray-core; se cancela por seguridad.\n' >&2
		return 1
	fi
	if [[ -e "$XRAY_ADMIN_BIN" ]]; then
		cp -a -- "$XRAY_ADMIN_BIN" "$backup_dir/xray" || return 1
		found=1
	fi
	for file in geoip.dat geosite.dat; do
		if [[ -e "$XRAY_ADMIN_DATA/$file" ]]; then
			cp -a -- "$XRAY_ADMIN_DATA/$file" "$backup_dir/$file" || return 1
			found=1
		fi
	done
	if [[ -e "$XRAY_ADMIN_MANIFEST" ]]; then
		[[ -f "$XRAY_ADMIN_MANIFEST" ]] || return 1
		cp -a -- "$XRAY_ADMIN_MANIFEST" "$backup_dir/xray-install.json" || return 1
		found=1
	fi
	if ((found)); then
		printf 'Respaldo de binario/geodata: %s
' "$backup_dir"
	else
		rmdir -- "$backup_dir" || return 1
		printf '%s
' 'No había binario ni geodata previos que respaldar.'
	fi
}

xray_admin_install_version() {
	local version="$1" mode="$2" workdir stage backup_parent backup_dir
	local backup_created=0 commit_started=0 committed=0 rollback_failed=0 file
	xray_admin_require_root || return 1
	xray_admin_require_tools || return 1
	case " $(xray_admin_compatible_versions | tr '
' ' ') " in
	*" $version "*) ;;
	*)
		printf 'La versión %s no está habilitada: falta adaptador compatible validado.
' "$version" >&2
		return 1
		;;
	esac
	case "$mode" in install | update | reinstall | repair) ;; *) return 2 ;; esac
	if [[ "${XRAY_MANAGER_LIFECYCLE_LOCK_HELD:-0}" != 1 ]]; then
		if ! manager_lock_acquire "${XRAY_MANAGER_LIFECYCLE_LOCK:-/run/lock/xray-manager-lifecycle.lock}" XRAY_ADMIN_LIFECYCLE_FD; then
			printf 'Hay otra operación de ciclo de vida del Manager en curso.\n' >&2
			return 1
		fi
	fi
	if ! xray_admin_lock; then
		if [[ "${XRAY_ADMIN_LIFECYCLE_FD:-}" =~ ^[0-9]+$ ]]; then
			manager_lock_release "$XRAY_ADMIN_LIFECYCLE_FD"
			unset XRAY_ADMIN_LIFECYCLE_FD
		fi
		return 1
	fi

	if [[ "$mode" == install && ! -e "$XRAY_ADMIN_BIN" && ( -e "$XRAY_ADMIN_DATA/geoip.dat" || -e "$XRAY_ADMIN_DATA/geosite.dat" || -e "$XRAY_ADMIN_MANIFEST" ) ]]; then
		printf 'Hay artefactos parciales o un manifiesto sin binario; no se sobrescribirán. Usa reparación tras revisar el estado.\n' >&2
		xray_admin_unlock
		return 1
	fi
	if [[ -e "$XRAY_ADMIN_BIN" || -L "$XRAY_ADMIN_BIN" ]]; then
		if [[ -L "$XRAY_ADMIN_BIN" ]]; then
			printf 'El destino del binario Xray es un enlace simbólico; se cancela.
' >&2
			xray_admin_unlock
			return 1
		fi
		case "$mode" in
		install)
			printf 'Xray-core ya existe. Usa actualizar o reinstalar.
' >&2
			xray_admin_unlock
			return 1
			;;
		update)
			local installed
			installed="$("$XRAY_ADMIN_BIN" version 2>/dev/null | head -n 1 || true)"
			if ! xray_admin_verify_installation; then
				printf 'La instalación existente no está verificada; no se actualizará. Ejecuta Reparar instalación tras revisar el diagnóstico.\n' >&2
				xray_admin_unlock
				return 1
			fi
			if [[ "$installed" == *"Xray $version "* ]]; then
				printf 'La versión %s ya está instalada y su integridad fue verificada.\n' "$version"
				xray_admin_unlock
				return 0
			fi
			;;
		reinstall)
			if ! xray_admin_verify_installation; then
				printf 'La instalación existente no está verificada; no se reinstalará. Usa Reparar instalación para recuperación explícita.\n' >&2
				xray_admin_unlock
				return 1
			fi
			;;
		repair) ;;
		esac
	elif [[ "$mode" == update || "$mode" == reinstall ]]; then
		printf 'No hay una instalación que actualizar o reinstalar.
' >&2
		xray_admin_unlock
		return 1
	fi

	if [[ -L "$XRAY_ADMIN_CACHE" || -L "$(dirname "$XRAY_ADMIN_CACHE")" ||
	-L "$XRAY_ADMIN_BACKUPS" || -L "$(dirname "$XRAY_ADMIN_BACKUPS")" ]]; then
		printf 'La caché o la ruta de respaldos de Xray contiene un enlace simbólico.\n' >&2
		xray_admin_unlock
		return 1
	fi
	if ! install -d -m 700 "$XRAY_ADMIN_CACHE"; then
		xray_admin_unlock
		return 1
	fi
	workdir="$(mktemp -d "$XRAY_ADMIN_CACHE/operation.XXXXXX")" || {
		xray_admin_unlock
		return 1
	}
	stage="$workdir/stage"
	backup_parent="$XRAY_ADMIN_BACKUPS"
	if ! install -d -m 700 "$backup_parent"; then
		rm -rf -- "$workdir"
		xray_admin_unlock
		return 1
	fi
	backup_dir="$(mktemp -d "$backup_parent/$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")" || {
		rm -rf -- "$workdir"
		xray_admin_unlock
		return 1
	}

	# shellcheck disable=SC2317
	xray_admin_cleanup() {
		if ((commit_started && committed == 0)); then
			if [[ -e "$backup_dir/xray" ]]; then
				if ! cp -a -- "$backup_dir/xray" "$XRAY_ADMIN_BIN.rollback" ||
					! mv -f -- "$XRAY_ADMIN_BIN.rollback" "$XRAY_ADMIN_BIN"; then
					rollback_failed=1
				fi
			elif ! rm -f -- "$XRAY_ADMIN_BIN.new" "$XRAY_ADMIN_BIN"; then
				rollback_failed=1
			fi
			for file in geoip.dat geosite.dat; do
				if [[ -e "$backup_dir/$file" ]]; then
					if ! install -d -m 755 "$XRAY_ADMIN_DATA" ||
						! cp -a -- "$backup_dir/$file" "$XRAY_ADMIN_DATA/$file.rollback" ||
						! mv -f -- "$XRAY_ADMIN_DATA/$file.rollback" "$XRAY_ADMIN_DATA/$file"; then
						rollback_failed=1
					fi
				elif ! rm -f -- "$XRAY_ADMIN_DATA/$file.new" "$XRAY_ADMIN_DATA/$file"; then
					rollback_failed=1
				fi
			done
			if [[ -e "$backup_dir/xray-install.json" ]]; then
				if ! install -d -m 700 "$(dirname "$XRAY_ADMIN_MANIFEST")" ||
					! cp -a -- "$backup_dir/xray-install.json" "$XRAY_ADMIN_MANIFEST.rollback" ||
					! mv -f -- "$XRAY_ADMIN_MANIFEST.rollback" "$XRAY_ADMIN_MANIFEST"; then
					rollback_failed=1
				fi
			elif ! rm -f -- "$XRAY_ADMIN_MANIFEST"; then
				rollback_failed=1
			fi
			if ((rollback_failed)); then
				printf 'ERROR: la restauración automática no pudo completarse. Usa el respaldo: %s
' "$backup_dir" >&2
			else
				printf 'Rollback de binario/geodata completado.
' >&2
			fi
		fi
		if ((backup_created)); then
			printf 'Respaldo previo conservado en: %s
' "$backup_dir" >&2
		else
			rm -rf -- "$backup_dir"
		fi
		rm -rf -- "$workdir"
		xray_admin_unlock
		return 0
	}
	trap xray_admin_cleanup RETURN

	printf 'Consultando release oficial y verificando SHA-256 de Xray-core %s...
' "$version"
	xray_admin_fetch_verified_release "$version" "$workdir" || return 1
	xray_admin_extract_stage "$version" "$workdir" "$stage" || return 1

	if [[ -L "$(dirname "$XRAY_ADMIN_BIN")" || -L "$XRAY_ADMIN_DATA" ]]; then
		printf 'Un directorio de destino de Xray es un enlace simbólico; se cancela.\n' >&2
		return 1
	fi
	install -d -m 755 "$(dirname "$XRAY_ADMIN_BIN")" "$XRAY_ADMIN_DATA" || return 1
	xray_admin_backup_existing "$backup_dir" || return 1
	[[ -d "$backup_dir" ]] && backup_created=1

	commit_started=1
	install -m 755 "$stage/xray" "$XRAY_ADMIN_BIN.new" || return 1
	install -m 644 "$stage/geoip.dat" "$XRAY_ADMIN_DATA/geoip.dat.new" || return 1
	install -m 644 "$stage/geosite.dat" "$XRAY_ADMIN_DATA/geosite.dat.new" || return 1
	"$XRAY_ADMIN_BIN.new" version | grep -F "Xray $version " >/dev/null || return 1
	mv -f -- "$XRAY_ADMIN_BIN.new" "$XRAY_ADMIN_BIN" || return 1
	mv -f -- "$XRAY_ADMIN_DATA/geoip.dat.new" "$XRAY_ADMIN_DATA/geoip.dat" || return 1
	mv -f -- "$XRAY_ADMIN_DATA/geosite.dat.new" "$XRAY_ADMIN_DATA/geosite.dat" || return 1
	chown root:root "$XRAY_ADMIN_BIN" "$XRAY_ADMIN_DATA/geoip.dat" "$XRAY_ADMIN_DATA/geosite.dat" || return 1
	chmod 755 "$XRAY_ADMIN_BIN" || return 1
	chmod 644 "$XRAY_ADMIN_DATA/geoip.dat" "$XRAY_ADMIN_DATA/geosite.dat" || return 1
	"$XRAY_ADMIN_BIN" version | grep -F "Xray $version " >/dev/null || return 1
	local package_sha256
	package_sha256="$(cat "$workdir/package.sha256")" || return 1
	xray_admin_record_installation "$version" "$package_sha256" || return 1
	committed=1
	printf '
Xray-core %s quedó instalado y su integridad fue registrada.
' "$version"
	printf 'No se creó ni reinició ningún servicio systemd.
'
	((backup_created)) && printf 'Respaldo previo conservado en: %s
' "$backup_dir"
	trap - RETURN
	rm -rf -- "$workdir"
	xray_admin_unlock
}

xray_admin_prepare_service_menu_action() {
	local lifecycle_fd lifecycle_lock result=0 own_lock=0
	ui_clear
	ui_title "PREPARAR SERVICIO XRAY-CORE"
	if ! xray_admin_verify_installation; then
		printf '\nLa instalación de Xray-core no está verificada (falta el manifiesto o hay una discrepancia). No se preparará el servicio.\n'
		printf 'Usa Reparar instalación para recuperar una instalación administrada o inspecciona el estado manualmente.\n'
		ui_pause
		return 1
	fi
	if ! declare -F xray_service_prepare >/dev/null 2>&1; then
		printf 'El módulo de preparación del servicio no está cargado.\n' >&2
		ui_pause
		return 1
	fi
	printf '\nSe verificaron el binario y los dos archivos geodata.\n'
	printf 'La preparación puede crear/verificar usuario y grupo, directorios y unidad xray.service, y recargar la configuración de systemd.\n'
	printf 'No iniciará ni habilitará el servicio.\n'
	if ! ui_confirm "¿Confirmas preparar la identidad y la unidad del servicio Xray-core?"; then
		printf 'Preparación cancelada.\n'
		ui_pause
		return 0
	fi

	if [[ "${XRAY_MANAGER_LIFECYCLE_LOCK_HELD:-0}" != 1 ]]; then
		lifecycle_lock="${XRAY_MANAGER_LIFECYCLE_LOCK:-/run/lock/xray-manager-lifecycle.lock}"
		if ! manager_lock_acquire "$lifecycle_lock" lifecycle_fd; then
			printf 'Hay otra operación de ciclo de vida del Manager en curso; no se preparó el servicio.\n' >&2
			ui_pause
			return 1
		fi
		own_lock=1
		XRAY_MANAGER_LIFECYCLE_LOCK_HELD=1
	fi

	# Revalidar bajo el bloqueo: evita TOCTOU entre la previsualización y la preparación.
	if ! xray_admin_verify_installation; then
		printf 'La integridad cambió o dejó de verificarse antes de preparar el servicio. No se modificó.\n' >&2
		result=1
	elif ! xray_service_prepare; then
		printf 'No se pudo preparar el servicio. Revisa el diagnóstico anterior.\n' >&2
		result=1
	fi

	if ((own_lock)); then
		unset XRAY_MANAGER_LIFECYCLE_LOCK_HELD
		manager_lock_release "$lifecycle_fd"
	fi
	ui_pause
	return "$result"
}


xray_admin_install_menu_action() {
	local mode="$1" version choice operation_rc=0 pause_rc=0
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
	ui_read_option "Selecciona la versión: " choice || return 0
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
		if xray_admin_install_version "$version" "$mode"; then
			:
		else
			operation_rc=$?
			printf 'ERROR: la operación de %s de Xray-core %s falló (código %s). Revisa los mensajes anteriores; no se considera instalada.\n' \
				"$mode" "$version" "$operation_rc" >&2
		fi
	else
		printf 'Operación cancelada.\n'
	fi

	# La pausa no debe ocultar el resultado de la operación principal.
	ui_pause || pause_rc=$?
	if ((operation_rc != 0)); then
		return "$operation_rc"
	fi
	return "$pause_rc"
}
