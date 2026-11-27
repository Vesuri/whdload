#!/usr/bin/env python3
"""tools/reloc.py [--write [--out FILE]] IMAGE PROFILE...: the relocation census for moving the
race block into fast memory (docs/internals.md, "Fast memory"), games/Vroom's tools/reloc.py
with the Multiplayer's addresses and tables.

IMAGE is chip memory from 0 at the program's entry ($3658, v1: `BOOT_BREAK=0x3658`, then
`gdb dump binary memory`). PROFILEs are aprof profiles of whole sessions (`gdb monitor aprof
start/stop` through tools/vmp.py, on the aprof FS-UAE). --write writes src/reloc.i.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location(
    'vroom_reloc', HERE.parents[2] / 'Vroom' / 'tools' / 'reloc.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

R.S, R.E = 0xB254, 0x1CBB0          # the race block (Vroom's $A924-$1B4FF)
R.LO, R.HI = 0x3600, 0x20000
R.MID = ((R.S + R.E) // 2) & ~1
# Tables of code addresses in the block: (address, count[, stride]).
R.CODE_TABLES = [(0x1967A, 16, 8)]
# Tables of word offsets to code: (first entry, end, base); the scaler's blit routines.
R.OFFSET_TABLES = [(0x19D5C, 0x19DC2, 0x19D5C)]
# bra.w tables reached through an address register: the bitmap scaler's.
R.BRANCH_TABLES = [0x1C55E]
# Tables of data addresses in the block.
R.DATA_TABLES = [(0x1202A, 2), (0x1136C, 1)]
# Code whose address only a long immediate or a computed branch holds: the blitter queue's
# interrupt handlers (stored in the queue at $12032), a pushed return address, code at $8458
# and a crash sequence state.
R.CODE_ADDRS = [0x11E4C, 0x11E74, 0x11E90, 0x11EB0, 0x11EDC, 0x11EFC, 0x11F38, 0x11F60,
                0x11F8C, 0x11A5C, 0x8458, 0xE27A]
# Data in the block whose address the code takes as a long immediate.
R.DATA_ADDRS = {0x1202A, 0x12032}
# Long immediates into the block that are not addresses in it.
R.NOT_ADDRS = set()


def main(argv):
    if '--write' in argv and '--out' not in argv:
        argv = argv + ['--out', str(HERE.parents[1] / 'src' / 'reloc.i')]
    R.main(argv)


if __name__ == '__main__':
    main(sys.argv[1:])
