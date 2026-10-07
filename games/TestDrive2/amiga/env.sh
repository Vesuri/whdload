#!/usr/bin/env bash
# Source this to load this machine's paths from amiga/local.env (ignored; see
# local.env.example) and put the Amiga toolchain on PATH. The environment wins.
_local="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/local.env"
if [ -f "$_local" ]; then
  while IFS= read -r _line || [ -n "$_line" ]; do
    case "$_line" in ''|'#'*|[!A-Za-z_]*) continue ;; esac
    _name=${_line%%=*}
    [ -n "${!_name:-}" ] || eval "export $_name=\"${_line#*=}\""
  done < "$_local"
fi
unset _local _line _name
for _var in KICKSTART_DIR AMIGA_TOOLCHAIN; do
  [ -n "${!_var:-}" ] || { echo "amiga/env.sh: $_var is not set: add it to amiga/local.env" >&2; return 1 2>/dev/null || exit 1; }
done
unset _var
export PATH="$AMIGA_TOOLCHAIN/bin:${AMIGA_PATH:+$AMIGA_PATH:}$PATH"
export KICKSTART="${KICKSTART:-$KICKSTART_DIR/kick31.rom}"
