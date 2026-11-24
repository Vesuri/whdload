#!/usr/bin/env python3
"""tools/reloc.py [--write [--out FILE]] [--no-seeds LO-HI] IMAGE PROFILE...: the relocation census for moving the race block
($A924-$1B4FF: the race's setup and loop, the race state, the renderer, the objects and the
scalers) into fast memory
(docs/internals.md, "Fast memory").

IMAGE is the memory at the program's entry ($3658, patches applied: `BOOT_BREAK=0x3658`, then
`gdb dump binary memory`). PROFILEs are aprof profiles (tools/vroom.py aprof, or a whole
session's `monitor aprof start/stop`) and Barto traces' PC sets (a .pkl of a dict keyed by
PC): their executed PCs seed a recursive disassembly of $3600-$1E000, with the code-pointer,
offset and branch tables below. Every long absolute operand into the block is a relocation: in the block
(IN, applied once to the copy) or outside it (OUT, applied in chip memory after every
`Fix`, only where the site still holds its value). Long immediates count only when they are
a decoded instruction's address or listed in DATA_ADDRS; the rest (constants such as
$FFFF) are listed as kept. Prints the census and the PC-relative references across the
block's edges, and the long words into the block outside decoded code that no table
explains (to review). --write writes src/reloc_<variant>.i (variant from the image name;
--out another file).
"""
import argparse
import collections
import pickle
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
import game_server  # noqa: F401,E402  (puts amigaxdev on the path)
from amigaxdev.aprof import parse_profile  # noqa: E402
from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000  # noqa: E402
from capstone import m68k as M  # noqa: E402

S, E = 0xA924, 0x1B500
LO, HI = 0x3600, 0x1E000
# Tables of code addresses in the block (dispatch tables: lea table,a0 ... jsr (a1)).
CODE_TABLES = [(0xB10E, 44), (0xCD90, 5), (0xCE3C, 5), (0xCEBC, 5), (0xE0BE, 4),
               (0x7D5C, 6), (0x7FC6, 6), (0x1803A, 16, 8)]
# Tables of word offsets to code: (first entry, end, base); the scaler's blit routines
# (move.w ($186DE,pc,d7.w),d7 / jsr ($186F6,pc,d7.w)). Zero entries are unused.
OFFSET_TABLES = [(0x186F6, 0x1875C, 0x186F6)]
# bra.w tables reached through an address register: the bitmap scaler's
# (lea $1AEF0(pc),a6 / jsr (0,a6,d6.w)).
BRANCH_TABLES = [0x1AEF0]
# Tables of data addresses in the block.
DATA_TABLES = [(0x11E36, 3), (0x11E42, 18), (0x11260, 2), (0x1069E, 1), (0x12390, 4)]
# Code whose address only a long immediate or a computed branch holds: the crash sequence's
# states (stored in $E0E4), the blitter queue's interrupt handlers (stored in the queue at
# $11268), a return address pushed at $10E44, and code at $7FFE.
CODE_ADDRS = [0xD78E, 0xD862, 0xD92C, 0xD9EA, 0x110A8, 0x110D0, 0x110EC, 0x1110C, 0x11138,
              0x11158, 0x11194, 0x111BC, 0x111E8, 0x10CF4, 0x7FFE]
# Data in the block whose address the code takes as a long immediate.
DATA_ADDRS = {0x10AEE, 0x11260, 0x11268}
ADDR_OPS = ('movea', 'adda', 'suba', 'cmpa', 'lea', 'pea')
# Instructions whose long immediate into the block is the base of an address outside it,
# kept as numbers: the title's install of a load routine into the loader
# (movea.l #$15294,a1 / lea 32000(a1),a1: $1D094).
NOT_ADDRS = {0x12F12}


MID = ((S + E) // 2) & ~1


def entries(tables):
    """(address, count[, stride]) tables: the addresses of their long entries."""
    for t in tables:
        a, n, st = (t + (4,))[:3]
        for k in range(n):
            yield a + st * k


def inb(a):
    return S <= a < E


def seeds_from(paths):
    s = {0x3658}
    for p in paths:
        if p.endswith('.pkl'):
            s |= set(pickle.load(open(p, 'rb')).keys())
        else:
            _h, pcs, _n = parse_profile(Path(p).read_text())
            s |= {x for x in pcs if x < 0x80000}
    return s


def long_at(mem, a):
    return struct.unpack_from('>I', mem, a)[0]


def disassemble(mem, seeds):
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
    md.detail = True
    code, bad = {}, set()
    todo = [x for x in seeds if LO <= x < HI]
    todo += [long_at(mem, x) for x in entries(CODE_TABLES)]
    for t in BRANCH_TABLES:
        while struct.unpack_from('>H', mem, t)[0] == 0x6000:
            todo.append(t)
            t += 4
    for lo, hi, base in OFFSET_TABLES:
        todo += [base + d for d in struct.unpack_from(f'>{(hi - lo) // 2}h', mem, lo) if d]
    todo += CODE_ADDRS
    while todo:
        pc = todo.pop()
        while LO <= pc < HI and pc not in code:
            got = list(md.disasm(mem[pc:pc + 10], pc, 1))
            if not got or got[0].id == 0:
                bad.add(pc)
                break
            i = got[0]
            try:
                ops = i.operands
            except Exception:
                bad.add(pc)
                break
            code[pc] = i
            m = i.mnemonic
            for o in ops:
                if o.type == M.M68K_OP_BR_DISP:
                    todo.append(pc + 2 + o.br_disp.disp)
            if m.startswith(('jsr', 'jmp')):
                for o in ops:
                    if o.type == M.M68K_OP_MEM and o.address_mode == M.M68K_AM_ABSOLUTE_DATA_LONG:
                        todo.append(o.imm)
                    if o.type == M.M68K_OP_MEM and o.address_mode == M.M68K_AM_PCI_DISP:
                        todo.append(pc + 2 + o.mem.disp)
            if m.startswith(('jmp', 'jsr')) and ops and ops[0].address_mode == M.M68K_AM_PCI_INDEX_8_BIT_DISP:
                t = pc + 2 + ops[0].mem.disp           # a branch table: bra.w entries
                while struct.unpack_from('>H', mem, t)[0] == 0x6000:
                    BRA_TABLES.add(pc)
                    todo.append(t)
                    t += 4
            if m.startswith(('movea.l', 'jmp', 'jsr')) and FIND_TABLES:
                hint_tables(mem, code, pc, i)
            if m.startswith(('rts', 'rte', 'rtr', 'jmp', 'bra', 'illegal')):
                break
            pc += i.size
    return code, bad


BRA_TABLES = set()
FIND_TABLES = False
FOUND = {}


def hint_tables(mem, code, pc, i):
    """movea.l (d,An,Xn),Am after a lea X,An: a long table around X (for review only)."""
    o = i.operands[0]
    if not (i.mnemonic.startswith('movea') and o.type == M.M68K_OP_MEM
            and o.address_mode == M.M68K_AM_AREGI_INDEX_8_BIT_DISP):
        return
    reg = o.mem.base_reg
    back = sorted(x for x in code if pc - 24 <= x < pc)
    for x in reversed(back):
        j = code[x]
        if j.mnemonic.startswith('lea') and j.operands[1].reg == reg:
            src = j.operands[0]
            if src.address_mode == M.M68K_AM_ABSOLUTE_DATA_LONG:
                base = src.imm
            elif src.address_mode == M.M68K_AM_PCI_DISP:
                base = x + 2 + src.mem.disp
            else:
                return
            base += o.mem.disp
            lo = hi = base
            ok = lambda v: v % 2 == 0 and LO <= v < HI
            while ok(long_at(mem, lo - 4)):
                lo -= 4
            while ok(long_at(mem, hi)):
                hi += 4
            if hi > lo:
                FOUND[lo] = ((hi - lo) // 4, pc)
            return


def census(mem, code):
    rel, kept, cross = [], [], []
    for pc, i in sorted(code.items()):
        b = mem[pc:pc + i.size]
        vals = []
        for o in i.operands:
            if o.type == M.M68K_OP_MEM and o.address_mode == M.M68K_AM_ABSOLUTE_DATA_LONG \
                    and inb(o.imm):
                vals.append(o.imm)
            if o.type == M.M68K_OP_IMM and i.mnemonic.endswith('.l'):
                v = o.imm & 0xFFFFFFFF
                if inb(v):
                    if pc in NOT_ADDRS:
                        kept.append((pc, v, f'{i.mnemonic} {i.op_str}'))
                    elif i.mnemonic.split('.')[0] in ADDR_OPS or v in code or v in DATA_ADDRS:
                        vals.append(v)
                    else:
                        kept.append((pc, v, f'{i.mnemonic} {i.op_str}'))
            t = None
            if o.type == M.M68K_OP_MEM and o.address_mode in (M.M68K_AM_PCI_DISP,
                                                             M.M68K_AM_PCI_INDEX_8_BIT_DISP):
                t = pc + 2 + o.mem.disp
            if o.type == M.M68K_OP_BR_DISP:
                t = pc + 2 + o.br_disp.disp
            if t is not None and inb(pc) != inb(t):
                cross.append((pc, t, f'{i.mnemonic} {i.op_str}'))
        off = 2
        for v in vals:
            j = b.find(struct.pack('>I', v), off)
            if j < 0:
                sys.exit(f'operand {v:#x} not found in {pc:#x}')
            rel.append((pc + j, v, f'{pc:05x}: {i.mnemonic} {i.op_str}'))
            off = j + 4
    for x in entries(CODE_TABLES + DATA_TABLES):
        v = long_at(mem, x)
        if inb(v):
            rel.append((x, v, 'table'))
    return sorted(set(rel)), kept, cross


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--out', help='the file --write writes (default src/reloc_<variant>.i)')
    ap.add_argument('--no-seeds', metavar='LO-HI',
                    help='leave the profiles\' PCs in this range out (hex; where the variant '
                    'differs from the profiled one, as the data disk\'s init code $3600-$4400)')
    ap.add_argument('image')
    ap.add_argument('profiles', nargs='+')
    a = ap.parse_args(argv)
    mem = open(a.image, 'rb').read()
    global FIND_TABLES
    FIND_TABLES = True
    seeds = seeds_from(a.profiles)
    if a.no_seeds:
        lo, hi = (int(x, 16) for x in a.no_seeds.split('-'))
        seeds = {x for x in seeds if not lo <= x < hi} | {0x3658}
    code, bad = disassemble(mem, seeds)
    known = {t[0] for t in CODE_TABLES + DATA_TABLES}
    print('long tables found after lea/movea (not in CODE_TABLES or DATA_TABLES; review):')
    for t, (n, pc) in sorted(FOUND.items()):
        if t not in known:
            print(f'  ${t:05X} {n} entries (at {pc:05x}): '
                  + ' '.join(f'{long_at(mem, t + 4 * k):x}' for k in range(min(n, 8))))
    rel, kept, cross = census(mem, code)
    covered = set()
    for pc, i in code.items():
        covered.update(range(pc, pc + i.size))
    tabled = set()
    for x in entries(CODE_TABLES + DATA_TABLES):
        tabled.update(range(x, x + 4))
    sites = {s for s, _v, _t in rel}
    review = [x for x in range(LO, HI - 3, 2)
              if inb(long_at(mem, x)) and x not in sites
              and not any(y in covered or y in tabled for y in range(x, x + 4))]
    ins = [r for r in rel if inb(r[0])]
    outs = [r for r in rel if not inb(r[0])]
    print(f'{len(code)} instructions decoded; undecodable targets: '
          + ' '.join(f'{x:x}' for x in sorted(bad)))
    print(f'relocations: {len(ins)} in the block, {len(outs)} outside it')
    print('long immediates in the block range kept as numbers:')
    for pc, v, t in kept:
        print(f'  {pc:05x} {t}')
    print('PC-relative references across the block edges:')
    for pc, t, s in cross:
        print(f'  {pc:05x} -> {t:05x}  {s}')
    print(f'long words into the block outside decoded code and tables: {len(review)}')
    for x in review:
        print(f'  {x:05x} {long_at(mem, x):08x}')
    if a.write:
        variant = Path(a.image).stem.split('-')[-1]
        out = Path(a.out) if a.out else \
            Path(__file__).resolve().parents[1] / f'src/reloc_{variant}.i'
        lines = [f'; generated by tools/reloc.py from the {variant} program: the race',
                 f'; block ${S:X}-${E:X} moved to fast memory (src/enhanced.i, enh_Move).',
                 f'; RELOC_IN: (site-${MID:X})/2 of long addresses into the block in it',
                 '; RELOC_OUT: site/2 (a word) and the long address into it it holds, from outside',
                 'RELOC_IN', ]
        lines += [f'\t\tdc.w\t{(s - MID) // 2}\t\t; ${s:05X} {t}' for s, _v, t in ins]
        lines += ['\t\tdc.w\t$8000', 'RELOC_OUT']
        lines += [f'\t\tdc.w\t${s >> 1:04X}\n\t\tdc.l\t${v:05X}\t; ${s:05X} {t}' for s, v, t in outs]
        lines += ['\t\tdc.w\t0']
        out.write_text('\n'.join(lines) + '\n')
        print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1:])
