#!/bin/bash
# Disassemble gamemule hunk-0 offsets [START,END) from a dump: dis.sh START END [MEMDIR] [HUNKBASE]
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/../../common/env.sh"
M="${3:-$ROOT/tmp/prof/flight1-mem}"; H="${4:-0x985cd8}"
python3 -m amigaxdev.disasm ${CPUOPT:-} disd "$M/fast.bin" 0x200000 "$H" "$1" "$2"
