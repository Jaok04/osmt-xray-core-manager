#!/usr/bin/env bash

ui_clear() {
	if [[ -t 1 ]]; then
		clear
	else
		printf '\n'
	fi
}

ui_color_start() {
	[[ -t 1 && -z "${NO_COLOR:-}" ]] || return 0
	case "${APP_THEME:-cyan}" in
	cyan) printf '\033[36m' ;;
	green) printf '\033[32m' ;;
	blue) printf '\033[34m' ;;
	magenta) printf '\033[35m' ;;
	esac
}

ui_color_end() {
	if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
		printf '\033[0m'
	fi
	return 0
}

ui_line() {
	ui_color_start
	printf '%s\n' '══════════════════════════════════════════════════════════════════════'
	ui_color_end
}

ui_pause() {
	local unused
	printf '\nPresiona ENTER para continuar...'
	# shellcheck disable=SC2034
	IFS= read -r unused || true
}

ui_read_option() {
	local prompt="$1"
	local destination="$2"
	local answer
	printf '%s' "$prompt"
	if ! IFS= read -r answer; then
		answer=''
	fi
	printf -v "$destination" '%s' "$answer"
}

ui_confirm() {
	local prompt="$1"
	local answer
	printf '%s [s/N]: ' "$prompt"
	if ! IFS= read -r answer; then
		return 1
	fi
	case "${answer,,}" in
	s | si | sí | y | yes) return 0 ;;
	*) return 1 ;;
	esac
}

ui_title() {
	local title="$1"
	ui_line
	ui_color_start
	printf '  %s\n' "$title"
	ui_color_end
	ui_line
}
