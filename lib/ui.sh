#!/usr/bin/env bash

ui_clear() {
	if [[ -t 1 ]]; then
		clear
	else
		printf '\n'
	fi
}

ui_line() {
	printf '%s\n' '══════════════════════════════════════════════════════════════════════'
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
	printf '  %s\n' "$title"
	ui_line
}