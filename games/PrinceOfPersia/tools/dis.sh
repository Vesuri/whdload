#!/bin/bash
# dis.sh PROF START END: disassemble game code by original address from a profile's slow.bin
# (reloc_base $d25000, as on the a500-1.5m captures).
PYTHONPATH="${AMIGA_PYLIB:-$HOME/.local/share/amiga/pylib}" exec python3 -m amigaxdev.disasm disd "$1/slow.bin" 0xc00000 $((0xd25000-0x1000)) "$2" "$3"
