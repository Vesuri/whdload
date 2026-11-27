#!/usr/bin/env python3
"""tools/reloc.py [--write [--out FILE]] IMAGE PROFILE...: the relocation census for moving the
race block into fast memory (docs/internals.md, "Fast memory"), games/Vroom's tools/reloc.py
with the Multiplayer's addresses and tables.

IMAGE is chip memory from 0 at the program's entry ($3658, v1: `BOOT_BREAK=0x3658`, then
`gdb dump binary memory`), from the slave with every patch (CUSTOM1=1 on a 68020 or higher):
the tables must not relocate an operand a patch has replaced. PROFILEs are aprof profiles of whole sessions (`gdb monitor aprof
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
# Tables of code addresses in the block: (address, count[, stride]): the scaler's, the race
# setup's dispatch ($BB18), the crash sequences' states ($D74A, $D900, $D980, $E9F2).
R.CODE_TABLES = [(0x1967A, 16, 8), (0xBB18, 22), (0xD74A, 5), (0xD900, 5), (0xD980, 5),
                 (0xE9F2, 4)]
# Tables of word offsets to code: (first entry, end, base); the scaler's blit routines.
R.OFFSET_TABLES = [(0x19D5C, 0x19DC2, 0x19D5C)]
# bra.w tables reached through an address register: the bitmap scaler's.
R.BRANCH_TABLES = [0x1C55E]
# Tables of data addresses in the block.
R.DATA_TABLES = [(0x1202A, 2), (0x1136C, 1), (0xE568, 4, 8), (0x11452, 3), (0x11480, 1),
                 (0x133F4, 21), (0x139B2, 4), (0x128AE, 1), (0x128C4, 1)]
# Code whose address only a long immediate or a computed branch holds: the blitter queue's
# interrupt handlers (stored in the queue at $12032), a pushed return address, code at $8458
# and the crash sequences' states (stored in $46 of a player's block, called at $DC5E).
R.CODE_ADDRS = [0x11E4C, 0x11E74, 0x11E90, 0x11EB0, 0x11EDC, 0x11EFC, 0x11F38, 0x11F60,
                0x11F8C, 0x11A5C, 0x8458, 0xE27A, 0xE17E, 0xE0A0, 0xE31C]
# Data in the block whose address the code takes as a long immediate.
R.DATA_ADDRS = {0x1202A, 0x12032}
# Instructions whose long immediate falls in the block without being an address in it: a
# speed clamp ($1B800) and screen sizes added to or taken from a screen pointer ($FA00, $EA60).
R.NOT_ADDRS = {0xF722, 0xF72A, 0x14350, 0x143B8, 0x816E, 0x820C, 0x8230}


# Instructions that hold an address operand: a long into the block just after one of these
# opcodes, outside the decoded code, seeds the disassembly (code no profile ran: the menu's
# and the results' routines, the crash sequences).
SEED_OPS = ('jsr', 'jmp', 'lea', 'pea', 'move', 'movea', 'cmp', 'cmpa', 'tst', 'add', 'sub',
            'clr', 'adda', 'suba')
_disassemble = R.disassemble


def disassemble(mem, seeds):
    from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000
    import struct
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
    seeds = set(seeds)
    while True:
        code, bad = _disassemble(mem, seeds)
        covered = set()
        for pc, i in code.items():
            covered.update(range(pc, pc + i.size))
        new = set()
        for x in range(R.LO, R.HI - 3, 2):
            v = struct.unpack_from('>I', mem, x)[0]
            if not R.inb(v) or x in covered:
                continue
            for back in (2, 4):
                got = list(md.disasm(mem[x - back:x - back + 10], x - back, 1))
                if got and got[0].mnemonic.split('.')[0] in SEED_OPS \
                        and got[0].size >= back + 4 and x - back not in covered:
                    new.add(x - back)
                    break
        new -= seeds
        if not new:
            return code, bad
        seeds |= new


R.disassemble = disassemble


def main(argv):
    if '--write' in argv and '--out' not in argv:
        argv = argv + ['--out', str(HERE.parents[1] / 'src' / 'reloc.i')]
    R.main(argv)


if __name__ == '__main__':
    main(sys.argv[1:])
