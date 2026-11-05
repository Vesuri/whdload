#!/usr/bin/env python3
"""F5: relocating copies of the game code, with instructions allowed to grow.

  . ../../common/env.sh; python3 tools/translate.py [--check DUMPDIR]

M1, S3 and F2 copy game code to fast RAM at its original length, so an absolute short
(`$1240.w`) or 16-bit displacement (`$840(a0)`) operand can never reach fast RAM. This
generator decodes the copied blocks (and the F5 blocks below) from the game's Disk.1 and
writes src/translate-f5.i: per block an edit recipe that the slave applies while
copying, the map from original to copied addresses, island stubs and entries. No game
bytes are emitted: the recipe copies runs of the loaded image and changes only opcode mode
bits, displacements and addresses.

Rewrites (68020 and later):
- `(d16,An)` with d16 in a moved data range: full-format `(bd.l,An)` (+4 bytes).
- `abs.w` in a moved range: `abs.l` (+2).
- Branches, DBcc and PC-relative operands inside a block are re-targeted; byte branches
  that no longer reach become word branches (+2).
Branches that leave a block go through JMP islands after it (as S3/F2 do).

The decode is recursive from the entries and every reference found by a whole-program
descent; bytes it does not reach are copied verbatim ("rigid": computed-jump tables, data)
and may not contain or straddle a growth point. --check DUMPDIR compares the slave's
translated copies, dumped from a running game (tools/memory_dump.py), with the generator's
expectation and decodes both for an operand-by-operand comparison.
"""
import argparse
import collections
import os
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000, CS_MODE_M68K_020
from capstone.m68k_const import (M68K_OP_BR_DISP, M68K_OP_MEM, M68K_OP_IMM, M68K_OP_REG,
                                 M68K_OP_REG_BITS, M68K_AM_REGI_ADDR_DISP,
                                 M68K_AM_ABSOLUTE_DATA_SHORT, M68K_AM_ABSOLUTE_DATA_LONG,
                                 M68K_AM_PCI_DISP, M68K_AM_PCI_INDEX_8_BIT_DISP,
                                 M68K_AM_IMMEDIATE, M68K_REG_A7)

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(os.environ.get('GAME_DRAWER', ROOT / 'tmp/game/Mercenary3_v1.2_0356/Mercenary3'))
OUT = ROOT / 'src/translate-f5.i'
D = 0x3cb0                       # chip address + D = Disk.1 offset
IMAGE, IMAGE_END = 0x5350, 0x5350 + 0x6d7b0

# Moved data: chip range -> offset in the slave's F5 data area (DATAMEM). The render
# scratch keeps its chip address in the low bits (area + chip address).
MOVED = [(0x0340, 0x4080, 0x0000)]   # the $3E18 cell array (4-byte entries) ends at $4070

# Blocks added by F5 to F2's (chip addresses; Disk.1 in comments). They hold the remaining
# code that indexes the render scratch: room path between F2's two room blocks, room and
# object building, the object window, interior cells.
F5_BLOCKS = [
    (0x5f61c - D, 0x5fa40 - D),   # room path: cells, between F2 $5F422 and $5FA40
    (0x5ea34 - D, 0x5f328 - D),   # room building after the clear, up to F2 $5F328
    (0x57374 - D, 0x5765e - D),   # object window ($5743A..$57608), up to F2 $5765E
    (0x5a644 - D, 0x5a6e8 - D),   # lift: interior cell flags ($5A64C, $5A6DA)
    (0x5d6d4 - D, 0x5d78c - D),   # room counter ($5D6E6)
]
# Operands that only look like scratch addresses. $5D9CE: lea $3fc.w,a0 is object
# index 255 (times 4) for the object arrays ($581E(a0), ...), as at $5727A and $59876.
# $5DCDE..$5DD1E: a1 = a0 + $5350 points into the variables. $593D6: move.b $4070(a0),d3
# reads the edge byte array $4070..$416F (a0 up to $FC, as $4160.w/$4168.w at $59444), which
# starts inside the moved range but is written in chip.
NOT_SCRATCH = {0x5d9ce - D, 0x5dcde - D, 0x5dcf6 - D, 0x5dcfc - D, 0x5dd1e - D, 0x593d6 - D}
# Displacements of display-plane offsets ($1F40 per plane), never scratch.
PLANE = [(0x1f00, 0x1f80), (0x3e40, 0x3ec0)]

M1_BLOCKS = [(0x4b134, 0x4b2e2), (0x57380, 0x57c68)]
M1_ENTRIES = [0x4b134, 0x4b1c6, 0x4b1d8, 0x57380, 0x57388, 0x573a0, 0x57914]


def rd16(b, o):
    return struct.unpack_from('>H', b, o)[0]


def sx16(v):
    return v - 0x10000 if v & 0x8000 else v


def sx8(v):
    return v - 0x100 if v & 0x80 else v


class Image:
    def __init__(self):
        disk = (GAME / 'Disk.1').read_bytes()
        self.raw = bytearray(0x80000)
        self.raw[IMAGE:IMAGE_END] = disk[0x9000:0x9000 + IMAGE_END - IMAGE]
        self.md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
        self.md.detail = True
        self.cache = {}

    def dec(self, p):
        if p not in self.cache:
            self.cache[p] = next(self.md.disasm(bytes(self.raw[p:p + 22]), p), None)
        return self.cache[p]

    def word(self, p):
        return rd16(self.raw, p)


def table(text, label):
    return text.split(label, 1)[1].split('dc.l\t0', 1)[0]


def slave_tables():
    f2 = (ROOT / 'src/renderer-f2.i').read_text()
    ranges = [(int(a, 16) - D, int(b, 16) - D) for a, b, _ in
              re.findall(r'dc\.l\s+\$(\w+)-\$3cb0,\$(\w+)-\$3cb0,\$(\w+)', table(f2, '_f2_ranges'))]
    operands = [int(a, 16) - D for a in re.findall(r'\$(\w+)-\$3cb0', table(f2, '_f2_operands'))]
    entries = [int(a, 16) - D for a in re.findall(r'\$(\w+)-\$3cb0', table(f2, '_f2_entries'))]
    return ranges, operands, entries


# ---------------------------------------------------------------------------- decoding

def descend(img, roots, inside, code, stop_outside=True):
    """Recursive descent; code: {addr: insn}. Follows branches and absolute jumps."""
    todo, bad, indirect = list(roots), [], []
    while todo:
        p = todo.pop()
        while p not in code and IMAGE <= p < IMAGE_END and not p & 1 and (not stop_outside or inside(p)):
            i = img.dec(p)
            if i is None or not i.id:
                bad.append(p)
                break
            code[p] = i
            mn = i.mnemonic.split('.')[0]
            for op in i.operands:
                if op.type == M68K_OP_BR_DISP:
                    todo.append(p + 2 + op.br_disp.disp)
            if mn in ('jmp', 'jsr'):
                op = i.operands[0]
                if op.address_mode in (M68K_AM_ABSOLUTE_DATA_LONG, M68K_AM_ABSOLUTE_DATA_SHORT):
                    todo.append(op.imm & 0xffffffff)
                elif op.address_mode == M68K_AM_PCI_DISP:
                    todo.append(p + 2 + op.mem.disp)
                else:
                    indirect.append(p)
            if mn in ('rts', 'rte', 'rtr', 'jmp', 'bra', 'illegal', 'stop'):
                break
            p += i.size
    return bad, indirect


def whole_program(img):
    """Game code reachable from the entry, plus code-pointer immediates that decode."""
    code = {}
    descend(img, [0x4b100], lambda p: True, code)
    for _ in range(4):
        ptr = set()
        for p, i in list(code.items()):
            mn = i.mnemonic.split('.')[0]
            for op in i.operands:
                if ((op.type == M68K_OP_IMM and mn in ('move', 'movea')) or
                        (op.address_mode == M68K_AM_ABSOLUTE_DATA_LONG and mn in ('lea', 'pea'))):
                    t = op.imm & 0xffffffff
                    if IMAGE <= t < IMAGE_END and not t & 1 and t not in code:
                        ptr.add(t)
        ok = [t for t in ptr if not descend(img, [t], lambda p: True, dict(code))[0]]
        if not ok:
            break
        descend(img, ok, lambda p: True, code)
    return code


# ------------------------------------------------------------------ operand layout

def ea_ext_size(op, size_char):
    m = op.address_mode
    if op.type == M68K_OP_MEM or op.type == M68K_OP_IMM:
        if m in (M68K_AM_REGI_ADDR_DISP, M68K_AM_PCI_DISP, M68K_AM_ABSOLUTE_DATA_SHORT):
            return 2
        if m in (M68K_AM_PCI_INDEX_8_BIT_DISP,) or m == 8:   # (d8,An,Xn)
            return 2
        if m == M68K_AM_ABSOLUTE_DATA_LONG:
            return 4
        if m == M68K_AM_IMMEDIATE:
            return 4 if size_char == 'l' else 2
    return 0


def layout(img, p, i):
    """[(operand index, ext offset in instruction, ext size)] for every operand with
    extension words; asserts the sizes add up to the instruction length."""
    mn = i.mnemonic
    base = mn.split('.')[0]
    sz = mn[-1] if '.' in mn else 'w'
    ops = list(i.operands)
    out, off = [], 2
    if base == 'movem':
        off = 4                          # register mask first
        for k, op in enumerate(ops):
            n = ea_ext_size(op, sz)
            if n:
                out.append((k, off, n))
                off += n
    else:
        for k, op in enumerate(ops):
            if op.type == M68K_OP_IMM and base in ('addq', 'subq', 'moveq', 'trap') :
                continue
            if op.type == M68K_OP_IMM and base in ('asl', 'asr', 'lsl', 'lsr', 'rol', 'ror', 'roxl', 'roxr'):
                continue
            n = ea_ext_size(op, 'b' if base in ('btst', 'bset', 'bclr', 'bchg') and op.type == M68K_OP_IMM else sz)
            if base in ('btst', 'bset', 'bclr', 'bchg') and op.type == M68K_OP_IMM:
                n = 2
            if n:
                out.append((k, off, n))
                off += n
    if off != i.size:
        raise ValueError(f'layout mismatch at {p + D:05x}: {mn} {i.op_str} ({off} != {i.size})')
    return out


def ea_field(i, k):
    """'src' (bits 5..0) or 'dst' (MOVE destination, bits 11..6) for operand k."""
    base = i.mnemonic.split('.')[0]
    if base in ('move', 'movea') and k == len(i.operands) - 1 and len(i.operands) == 2:
        return 'dst'
    return 'src'


# ------------------------------------------------------------------------ the plan

class Block:
    def __init__(self, lo, hi, dest, offset=None):
        self.lo, self.hi, self.dest, self.offset = lo, hi, dest, offset
        self.items = []      # (addr, insn or None for data word, kind)
        self.edits = {}      # addr -> list of edit tuples
        self.size = None


def moved(addr):
    for lo, hi, off in MOVED:
        if lo <= addr < hi:
            return True
    return False


def plan(img, check_dump=None):
    f2_ranges, f2_operands, f2_entries = slave_tables()
    render = [(lo, hi) for lo, hi in f2_ranges] + F5_BLOCKS
    merged = []
    for lo, hi in sorted(render):
        if merged and merged[-1][1] == lo:
            merged[-1] = (merged[-1][0], hi)
        else:
            merged.append((lo, hi))
    blocks = [Block(lo, hi, 'hot') for lo, hi in M1_BLOCKS] + [Block(lo, hi, 'render') for lo, hi in merged]
    for b in blocks:
        for c in blocks:
            if b is not c and b.lo < c.hi and c.lo < b.hi:
                raise ValueError(f'overlapping blocks {b.lo + D:05x} {c.lo + D:05x}')

    def blk(p):
        return next((b for b in blocks if b.lo <= p < b.hi), None)

    prog = whole_program(img)
    # Roots: entries, and every reference from reached code (anywhere) into a block.
    roots = set(f2_entries) | set(M1_ENTRIES)
    for p, i in prog.items():
        for op in i.operands:
            if op.type == M68K_OP_BR_DISP:
                roots.add(p + 2 + op.br_disp.disp)
            if op.address_mode in (M68K_AM_ABSOLUTE_DATA_LONG,) or (op.type == M68K_OP_IMM and i.mnemonic.split('.')[0] in ('move', 'movea')):
                roots.add(op.imm & 0xffffffff)
        if p in prog:
            roots.add(p)
    roots = {r for r in roots if blk(r) and r in prog}
    # Computed jumps through a table of BRA.W right after jmp (d8,pc,Dn).
    tables = 0
    for p, i in list(prog.items()):
        if i.mnemonic == 'jmp' and i.operands[0].address_mode == M68K_AM_PCI_INDEX_8_BIT_DISP:
            t = p + 2 + i.operands[0].mem.disp
            if t != p + i.size:
                continue
            while img.word(t) == 0x6000 and blk(t):
                roots.add(t)
                t += 4
                tables += 1
    code = {}
    bad, indirect = descend(img, sorted(roots), lambda p: blk(p) is not None, code)
    if bad:
        raise ValueError('undecodable reached code: ' + ' '.join(f'{p + D:05x}' for p in bad))

    # Items: reached instructions, then linear decode of the gaps (rigid).
    for b in blocks:
        p = b.lo
        while p < b.hi:
            if p in code:
                i = code[p]
                if p + i.size > b.hi:
                    raise ValueError(f'instruction straddles block end {p + D:05x}')
                b.items.append((p, i, 'code'))
                p += i.size
                continue
            q = p
            while q < b.hi and q not in code:
                q += 2
            # rigid span p..q: linear decode for reference checks only
            r = p
            while r < q:
                i = img.dec(r)
                if i is None or not i.id or r + i.size > q:
                    b.items.append((r, None, 'data'))
                    r += 2
                else:
                    b.items.append((r, i, 'rigid'))
                    r += i.size
            p = q

    # A block may not be entered by falling through its start or leave by falling off its end.
    TERMINAL = ('rts', 'rte', 'rtr', 'jmp', 'bra', 'illegal')
    for b in blocks:
        prev = next((i for p, i in sorted(prog.items(), key=lambda kv: kv[0]) if False), None)
        before = [p for p in range(b.lo - 10, b.lo, 2) if p in prog and p + prog[p].size == b.lo]
        new = any(lo <= b.lo < hi or b.lo == hi for lo, hi in F5_BLOCKS)
        if before and new and prog[before[0]].mnemonic.split('.')[0] not in TERMINAL and b.lo in [lo for lo, hi in F5_BLOCKS]:
            raise ValueError(f'block {b.lo + D:05x} is entered by falling through from {before[0] + D:05x}')
        last = [(p, i) for p, i, k in b.items if k == 'code' and p + i.size == b.hi]
        if last and last[0][1].mnemonic.split('.')[0] not in TERMINAL:
            raise ValueError(f'block {b.lo + D:05x}..{b.hi + D:05x} falls off its end at {last[0][0] + D:05x}')
    # Words patched before the copy (by the slave) must not be edited.
    patched = set()
    if check_dump:
        chip = (Path(check_dump) / 'chip').read_bytes()
        stubs = set()
        for e in list(f2_entries) + M1_ENTRIES:
            stubs.update(range(e, e + 6))
        for a in range(IMAGE, IMAGE_END, 2):
            if chip[a:a + 2] != img.raw[a:a + 2] and a not in stubs:
                patched.add(a)

    # Choose rewrites.
    def scratch_disp(i, op):
        return (op.type == M68K_OP_MEM and op.address_mode == M68K_AM_REGI_ADDR_DISP
                and op.mem.base_reg != M68K_REG_A7 and moved(op.mem.disp & 0xffff)
                and op.mem.disp >= 0 and not any(lo <= op.mem.disp < hi for lo, hi in PLANE))

    growth = {}           # addr -> list of (ext offset, kind, value)
    for b in blocks:
        for p, i, kind in b.items:
            if kind != 'code' or p in NOT_SCRATCH:
                continue
            exts = None
            for k, op in enumerate(i.operands):
                hit = None
                if scratch_disp(i, op):
                    hit = ('disp', op.mem.disp)
                elif op.address_mode == M68K_AM_ABSOLUTE_DATA_SHORT and moved(op.imm & 0xffff):
                    hit = ('absw', op.imm & 0xffff)
                if not hit:
                    continue
                if i.mnemonic.startswith('movep'):
                    raise ValueError(f'movep into moved data at {p + D:05x}')
                exts = exts or layout(img, p, i)
                off = next(o for kk, o, n in exts if kk == k)
                growth.setdefault(p, []).append((off, hit[0], hit[1], ea_field(i, k)))
    return blocks, code, growth, patched, blk, prog, f2_operands, f2_entries, indirect


def build(img, blocks, code, growth, patched, blk):
    """Assign new sizes and addresses; returns per-block edits and maps."""
    # Instruction sizes after rewriting, before branch widening.
    widen = set()
    while True:
        newpos = {}
        for b in blocks:
            q = 0
            for p, i, kind in b.items:
                newpos[p] = q
                n = i.size if i else 2
                for off, k, v, f in growth.get(p, ()):
                    n += 4 if k == 'disp' else 2
                if p in widen:
                    n += 2
                q += n
            b.size = q
            newpos[('end', b.lo)] = q
        more = False
        import bisect
        for b in blocks:
            starts = [p for p, i, k in b.items]

            def at(t):
                q = starts[bisect.bisect_right(starts, t) - 1]
                return newpos[q] + (t - q)
            for p, i, kind in b.items:
                if kind != 'code' or i is None:
                    continue
                for op in i.operands:
                    if op.type != M68K_OP_BR_DISP or op.br_disp.disp_size != 1 or p in widen:
                        continue
                    t = p + 2 + op.br_disp.disp
                    if blk(t) is not b:
                        continue
                    d = at(t) - (newpos[p] + 2)
                    if not -128 <= d <= 127 or d in (0, -1):
                        widen.add(p)
                        more = True
        if not more:
            return newpos, widen


# ------------------------------------------------------------------------ emission

OP_END, OP_COPY, OP_SKIP, OP_XOR, OP_WORD, OP_EXTD, OP_SETLO, OP_EXTA = 0, 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x7000
FULL_BD_LONG = 0x0170        # full-format extension: no index, long base displacement


class Recipe:
    def __init__(self):
        self.ops = []        # (op, operand or None)
        self.out = 0         # output bytes so far
        self.src = 0         # input bytes consumed
        self.lo = 0
        self.touched = set() # original word addresses not copied verbatim

    def copy(self, nbytes):
        n = nbytes // 2
        if not n:
            return
        if self.ops and self.ops[-1][0] == OP_COPY and self.ops[-1][1] + n < 0x1000:
            self.ops[-1] = (OP_COPY, self.ops[-1][1] + n)
        else:
            while n:
                k = min(n, 0xfff)
                self.ops.append((OP_COPY, k))
                n -= k
        self.out += nbytes
        self.src += nbytes

    def skip(self, nbytes):
        self.touched.update(range(self.lo + self.src, self.lo + self.src + nbytes, 2))
        self.src += nbytes
        n = nbytes // 2
        if self.ops and self.ops[-1][0] == OP_SKIP and self.ops[-1][1] + n < 0x1000:
            self.ops[-1] = (OP_SKIP, self.ops[-1][1] + n)
        else:
            self.ops.append((OP_SKIP, n))

    def xor(self, v):
        self.touched.add(self.lo + self.src)
        self.ops.append((OP_XOR, v)); self.out += 2; self.src += 2

    def word(self, v):
        self.ops.append((OP_WORD, v & 0xffff)); self.out += 2

    def extd(self, a):
        """Replace a d16 word with the full-format extension and the moved address."""
        self.touched.add(self.lo + self.src)
        self.ops.append((OP_EXTD, a)); self.out += 6; self.src += 2

    def exta(self, a):
        """Replace an abs.w word with the moved address (abs.l)."""
        self.touched.add(self.lo + self.src)
        self.ops.append((OP_EXTA, a)); self.out += 4; self.src += 2

    def setlo(self, b):
        self.touched.add(self.lo + self.src)
        self.ops.append((OP_SETLO, b & 0xff)); self.out += 2; self.src += 2


def emit(img, blocks, code, growth, widen, newpos, blk):
    """Recipes, map thresholds and external branches for every block."""
    def target_pos(t):
        b = blk(t)
        return b, address_in(b, t)

    # Per-instruction internal remap for addresses inside rewritten instructions.
    inner = {}
    for p, g in growth.items():
        inner[p] = sorted((off + 2, 4 if k == 'disp' else 2) for off, k, v, f in g)
    for p in widen:
        inner.setdefault(p, []).append((2, 2))

    starts = {}
    for b in blocks:
        starts[b.lo] = [p for p, i, k in b.items]

    import bisect

    def address_in(b, a):
        lst = starts[b.lo]
        k = bisect.bisect_right(lst, a) - 1
        p = lst[k]
        extra = sum(n for th, n in inner.get(p, ()) if p + th <= a)
        return newpos[p] + (a - p) + extra

    recipes, islands, thresholds = {}, [], {}
    for b in blocks:
        r = Recipe()
        r.lo = b.lo
        th, total, last = [], 0, b.lo
        for p, i, kind in b.items:
            assert r.out == newpos[p], (hex(p + D), r.out, newpos[p])
            assert r.src == p - b.lo, (hex(p + D), r.src, p - b.lo, hex(last + D))
            last = p
            if i is None:
                r.copy(2)
                continue
            n = i.size
            if kind == 'rigid':
                for op in i.operands:
                    t = None
                    if op.type == M68K_OP_BR_DISP:
                        t = p + 2 + op.br_disp.disp
                    elif op.type == M68K_OP_MEM and op.address_mode in (M68K_AM_PCI_DISP, M68K_AM_PCI_INDEX_8_BIT_DISP):
                        t = p + 2 + op.mem.disp
                    if t is not None and not t & 1 and blk(t) is b and address_in(b, t) - newpos[p] != t - p:
                        raise ValueError(f'rigid reference across growth at {p + D:05x} -> {t + D:05x}')
                r.copy(n)
                continue
            mn = i.mnemonic.split('.')[0]
            brs = [op for op in i.operands if op.type == M68K_OP_BR_DISP]
            if brs:
                op = brs[0]
                t = p + 2 + op.br_disp.disp
                tb = blk(t)
                if tb is not b:
                    if op.br_disp.disp_size == 1:
                        raise ValueError(f'byte branch leaves its block at {p + D:05x}')
                    islands.append((b, p + 2 if mn not in ('dbra',) and not mn.startswith('db') else p + 2, t))
                    r.copy(n)
                    continue
                d = address_in(b, t) - (newpos[p] + 2)
                if op.br_disp.disp_size == 1:
                    if p in widen:
                        r.setlo(0)
                        r.word(d)
                        total += 2
                        th.append((p + 2, total))
                    else:
                        assert -128 <= d <= 127 and d not in (0, -1)
                        if d == op.br_disp.disp:
                            r.copy(2)
                        else:
                            r.setlo(d)
                    continue
                # word displacement after the opcode (Bcc.w, DBcc)
                assert n == 4, (hex(p + D), i.mnemonic)
                r.copy(2)
                if d == op.br_disp.disp:
                    r.copy(2)
                else:
                    r.word(d)
                    r.skip(2)
                continue
            g = {off: (k, v, f) for off, k, v, f in growth.get(p, ())}
            pcrel = [(k, op) for k, op in enumerate(i.operands)
                     if op.type == M68K_OP_MEM and op.address_mode in (M68K_AM_PCI_DISP, M68K_AM_PCI_INDEX_8_BIT_DISP)]
            if not g and not pcrel:
                r.copy(n)
                continue
            exts = layout(img, p, i)
            mask = 0
            for off, (k, v, f) in g.items():
                mask ^= {('disp', 'src'): 0x0018, ('disp', 'dst'): 0x00c0,
                         ('absw', 'src'): 0x0001, ('absw', 'dst'): 0x0200}[(k, f)]
            if mask:
                assert mask < 0x1000
                r.xor(mask)
            else:
                r.copy(2)
            pos = 2
            pcs = {}
            for k, op in pcrel:
                off = next(o for kk, o, nn in exts if kk == k)
                pcs[off] = op
            for k, off, nn in exts:
                if off > pos:
                    r.copy(off - pos)
                if off in g:
                    kind2, v, f = g[off]
                    if kind2 == 'disp':
                        r.extd(v)
                        total += 4
                    else:
                        r.exta(v)
                        total += 2
                    th.append((p + off + 2, total))
                elif off in pcs:
                    op = pcs[off]
                    ext = img.word(p + off)
                    if op.address_mode == M68K_AM_PCI_DISP:
                        t = p + off + sx16(ext)
                    else:
                        t = p + off + sx8(ext & 0xff)
                    tb = blk(t)
                    if tb is not b:
                        raise ValueError(f'PC-relative reference leaves its block at {p + D:05x}')
                    new = address_in(b, t) - address_in(b, p + off)
                    old = t - (p + off)
                    if op.address_mode == M68K_AM_PCI_DISP:
                        if new == old:
                            r.copy(2)
                        else:
                            assert -32768 <= new < 32768
                            r.word(new)
                            r.skip(2)
                    else:
                        if new == old:
                            r.copy(2)
                        else:
                            if not -128 <= new <= 127:
                                raise ValueError(f'PC index displacement overflows at {p + D:05x}')
                            r.setlo(new)
                else:
                    r.copy(nn)
                pos = off + nn
            if pos < n:
                r.copy(n - pos)
        assert r.out == b.size, (hex(b.lo + D), r.out, b.size)
        recipes[b.lo] = r
        thresholds[b.lo] = th
    return recipes, islands, thresholds, address_in


def place(blocks, islands, hot_limit, render_limit):
    """Destination offsets: M1 back to back in the hot area, the rest in the render area,
    each block followed by its JMP islands; original alignment mod 4 kept."""
    per = collections.defaultdict(list)
    for b, loc, t in islands:
        per[b.lo].append((loc, t))
    stubs = []
    cur = {'hot': 0, 'render': 0}
    for b in blocks:
        q = cur[b.dest]
        if b.dest == 'render':
            q = (q + 3) & ~3
            q += (b.lo - q) & 2 if False else 0
        b.offset = q
        q += b.size
        q = (q + 1) & ~1
        for loc, t in per[b.lo]:
            stubs.append((b, loc, t, q))
            q += 6
        cur[b.dest] = q
    if cur['hot'] > hot_limit or cur['render'] > render_limit:
        raise ValueError(f'translated code does not fit: hot {cur["hot"]:#x}/{hot_limit:#x}, '
                         f'render {cur["render"]:#x}/{render_limit:#x}')
    return stubs, cur


def references(img, prog, blocks, blk, new_blocks):
    """Entries (chip stubs) into F5's new blocks from untranslated code, and absolute
    operand slots anywhere whose value lies in a new block."""
    entries, slots = set(), set()
    newb = lambda a: any(lo <= a < hi for lo, hi in new_blocks)
    for p, i in prog.items():
        inside = blk(p) is not None
        mn = i.mnemonic.split('.')[0]
        for k, op in enumerate(i.operands):
            if op.type == M68K_OP_BR_DISP:
                t = p + 2 + op.br_disp.disp
                if not inside and newb(t):
                    entries.add(t)
            is_abs = op.address_mode == M68K_AM_ABSOLUTE_DATA_LONG
            is_imm = op.type == M68K_OP_IMM and mn in ('move', 'movea') and i.mnemonic.endswith('.l')
            if (is_abs or is_imm) and newb(op.imm & 0xffffffff):
                exts = layout(img, p, i)
                off = next(o for kk, o, n in exts if kk == k)
                slots.add(p + off)
    return entries, slots


def datamap_py(a, base):
    for lo, hi, off in MOVED:
        if lo <= a < hi:
            return base + off + a
    raise ValueError(hex(a))


def simulate(img, blocks, recipes, expmem, data_base):
    """Apply the recipes as the slave does; returns {block lo: bytes}."""
    out = {}
    for b in blocks:
        src, dst = b.lo, bytearray()
        for op, v in recipes[b.lo].ops:
            if op == OP_COPY:
                dst += img.raw[src:src + 2 * v]; src += 2 * v
            elif op == OP_SKIP:
                src += 2 * v
            elif op == OP_XOR:
                dst += struct.pack('>H', img.word(src) ^ v); src += 2
            elif op == OP_WORD:
                dst += struct.pack('>H', v)
            elif op == OP_EXTD:
                dst += struct.pack('>HI', FULL_BD_LONG, datamap_py(v, data_base)); src += 2
            elif op == OP_EXTA:
                dst += struct.pack('>I', datamap_py(v, data_base)); src += 2
            elif op == OP_SETLO:
                dst += struct.pack('>H', (img.word(src) & 0xff00) | v); src += 2
        assert src == b.hi, (hex(b.lo + D), hex(src + D))
        out[b.lo] = bytes(dst)
    return out


def verify(img, blocks, out, newpos, growth, address_in, blk, base_of, data_base):
    """Decode every translated code item (68020) and compare with the original."""
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_020)
    md.detail = True
    n = 0
    for b in blocks:
        data, base = out[b.lo], base_of(b)
        for p, i, kind in b.items:
            if kind != 'code':
                continue
            q = newpos[p]
            j = next(md.disasm(data[q:q + 22], base + q), None)
            if j is None:
                raise ValueError(f'undecodable translation of {p + D:05x}')
            mi, mj = i.mnemonic, j.mnemonic
            if mi != mj and not (mi.split('.')[0] == mj.split('.')[0] and mi.startswith('b')):
                raise ValueError(f'{p + D:05x}: {mi} {i.op_str} -> {mj} {j.op_str}')
            g = {}
            if p in growth:
                exts = layout(img, p, i)
                offk = {o: kk for kk, o, nn in exts}
                for off, k, v, f in growth[p]:
                    g[offk[off]] = (k, v)
            for k, (a, c) in enumerate(zip(i.operands, j.operands)):
                if a.type == M68K_OP_BR_DISP:
                    t = p + 2 + a.br_disp.disp
                    tj = q + base + 2 + c.br_disp.disp
                    if blk(t) is b:
                        want = base + address_in(b, t)
                        if tj != want:
                            raise ValueError(f'{p + D:05x}: branch to {tj:#x}, want {want:#x}')
                    continue
                if k in g:
                    kind2, v = g[k]
                    want = datamap_py(v, data_base)
                    if kind2 == 'disp':
                        ok = (c.type == M68K_OP_MEM and c.address_mode == 8 and c.mem.base_reg == a.mem.base_reg
                              and (c.mem.in_disp & 0xffffffff) == want and c.mem.index_reg == 0)
                    else:
                        ok = c.address_mode == M68K_AM_ABSOLUTE_DATA_LONG and (c.imm & 0xffffffff) == want
                    if not ok:
                        raise ValueError(f'{p + D:05x}: {i.op_str} -> {j.op_str}')
                    continue
                if a.type == M68K_OP_MEM and a.address_mode in (M68K_AM_PCI_DISP, M68K_AM_PCI_INDEX_8_BIT_DISP):
                    continue           # checked by construction (address_in); decoded below
                sa, sc = op_text(a), op_text(c)
                if sa != sc:
                    raise ValueError(f'{p + D:05x}: operand {k} {i.op_str} -> {j.op_str}')
            n += 1
    return n


def op_text(op):
    if op.type == M68K_OP_REG:
        return ('r', op.reg)
    if op.type == M68K_OP_IMM:
        return ('i', op.imm)
    if op.type == M68K_OP_MEM:
        return ('m', op.address_mode, op.mem.base_reg, op.mem.index_reg, op.mem.index_size,
                op.mem.disp, op.imm if op.address_mode in (M68K_AM_ABSOLUTE_DATA_SHORT, M68K_AM_ABSOLUTE_DATA_LONG) else 0)
    return ('o', op.type, getattr(op, 'register_bits', 0))


def write_table(blocks, recipes, thresholds, stubs, entries, slots, f2_operands):
    X = lambda a: f'${a + D:05x}-$3cb0'
    L = ['; F5 translation tables, generated by tools/translate.py from the game\'s Disk.1.',
         '; Disk.1 offsets, layout values and data addresses only; no game bytes.',
         '; Blocks: original start, end, destination (from ws_ExpMem), recipe, map (offset',
         '; in the block from which the translation has grown by so many bytes).',
         '_f5_blocks']
    for k, b in enumerate(blocks):
        dest = ('F5HOT' if b.dest == 'hot' else 'F5RENDER') + f'+${b.offset:x}'
        L.append(f'\tdc.l\t{X(b.lo)},{X(b.hi)},{dest},_f5_r{k}-_f5_blocks,_f5_t{k}-_f5_blocks')
    L += ['\tdc.l\t0', '; Moved data: chip start, end, offset in the F5 data area (+ chip address).',
          '_f5_data']
    for lo, hi, off in MOVED:
        L.append(f'\tdc.l\t${lo:x},${hi:x},${off:x}')
    L += ['\tdc.l\t0', '; JMP islands: branch displacement, target, island (from ws_ExpMem).', '_f5_branches']
    for b, loc, t, q in stubs:
        dest = ('F5HOT' if b.dest == 'hot' else 'F5RENDER') + f'+${q:x}'
        L.append(f'\tdc.l\t{X(loc)},{X(t)},{dest}')
    L += ['\tdc.l\t0', '; Chip entries of the F5 blocks (F2 and M1 entries are installed as before).',
          '_f5_entries']
    for e in sorted(entries):
        L.append(f'\tdc.l\t{X(e)}')
    L += ['\tdc.l\t0', '; Absolute operands that point into F5 blocks (after F2\'s).', '_f5_operands']
    for s in sorted(slots - set(f2_operands)):
        L.append(f'\tdc.l\t{X(s)}')
    L.append('\tdc.l\t0')
    words = 0
    for k, b in enumerate(blocks):
        L.append(f'_f5_r{k}')
        line = []
        for op, v in recipes[b.lo].ops:
            if op in (OP_COPY, OP_SKIP, OP_SETLO, OP_XOR):
                line.append(f'${op | v:04x}')
            else:
                line.append(f'${op:04x},${v:04x}')
        line.append('0')
        for c in range(0, len(line), 12):
            L.append('\tdc.w\t' + ','.join(line[c:c + 12]))
        words += sum(x.count(',') + 1 for x in line)
        assert all(not (op == OP_XOR and v >= 0x1000) for op, v in recipes[b.lo].ops)
        L.append(f'_f5_t{k}')
        th = [f'${a - b.lo:04x},{g}' for a, g in thresholds[b.lo]] + ['$ffff']
        assert b.hi - b.lo < 0xffff
        for c in range(0, len(th), 8):
            L.append('\tdc.w\t' + ','.join(th[c:c + 8]))
    L.append('\teven')
    OUT.write_text('\n'.join(L) + '\n')
    return words


def check(dump, img, blocks, recipes, stubs, newpos, address_in, blk, slots, entries):
    """Compare the slave's translations in a running game's dump with the simulation."""
    d = Path(dump)
    expmem = int((d / 'expmem.txt').read_text(), 16)
    exp = (d / 'exp').read_bytes()
    F5HOT, F5RENDER = 0x1000, 0x1000 + 0x1000 + 0x7000 + 0x5000
    F5DATA = F5RENDER + 0x1a000 + 0x18000 + 0x3000
    src = Image()
    src.raw[:] = (d / 'chip').read_bytes()          # the source as the slave patched it
    # The slave translates before it writes F5's chip entry jumps over the source.
    for e in entries:
        src.raw[e:e + 6] = img.raw[e:e + 6]
    out = simulate(src, blocks, recipes, expmem, expmem + F5DATA)
    # Words the slave writes after translating: island displacements, operand slots,
    # and the F2/M1 entry words (hooked in chip before the copy, then replaced by jumps).
    later = set()
    for b, loc, t, q in stubs:
        later.add(loc)
    for s_ in slots:
        later.update((s_, s_ + 2))
    later.update(range(0x4ee82 - D, 0x4ef92 - D, 2))     # F4's routine and its bra.s
    for e in list(slave_tables()[2]) + M1_ENTRIES:
        later.update(range(e, e + 6, 2))
    for a in (0x5366c, 0x5380a, 0x53822, 0x53668, 0x5368e, 0x536be, 0x577c8, 0x57c36):
        later.update(range(a - D, a - D + 6, 2))       # clip and object hooks
    total = bad = 0
    for b in blocks:
        off = (F5HOT if b.dest == 'hot' else F5RENDER) + b.offset
        got = exp[off:off + b.size]
        want = out[b.lo]
        for q in range(0, b.size, 2):
            if got[q:q + 2] != want[q:q + 2]:
                # back to the original address
                orig = next((p for p, i, k in reversed(b.items) if newpos[p] <= q), b.lo)
                total += 1
                if not any(orig <= a < orig + 10 for a in later):
                    bad += 1
                    if bad <= 20:
                        print(f'  differs: block {b.lo + D:05x} +{q:#x} (instruction {orig + D:05x}) '
                              f'{got[q:q + 2].hex()} != {want[q:q + 2].hex()}')
    print(f'check: {total} words differ, {bad} not at island/operand slots')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dump', help='a dump directory (chip): refuse edits in words patched before the copy')
    ap.add_argument('--check', help='compare with the translated code in a dump directory (chip, exp, expmem.txt)')
    args = ap.parse_args()
    img = Image()
    blocks, code, growth, patched, blk, prog, f2_operands, f2_entries, indirect = plan(img, args.dump or args.check)
    newpos, widen = build(img, blocks, code, growth, patched, blk)
    recipes, islands, thresholds, address_in = emit(img, blocks, code, growth, widen, newpos, blk)
    # Edited words must not have been patched by the slave before the copy.
    if patched:
        for p, g in growth.items():
            touched = {p} | {p + off for off, *_ in g}
            if touched & patched:
                raise ValueError(f'rewrite of a patched instruction at {p + D:05x}')
        for p in widen:
            if p in patched:
                raise ValueError(f'widened branch is patched at {p + D:05x}')
    # Words the slave patches in the copies after translation (mapped addresses).
    slave = (ROOT / 'src/Mercenary3.slave.asm').read_text()
    foreign = set()
    for a in re.findall(r'move\.l\t#\$([0-9a-f]+)-\$3cb0,d0', slave):
        foreign.update(range(int(a, 16) - D, int(a, 16) - D + 6, 2))
    rr = slave.split('_restore_ranges', 2)[2].split('_restore_clip')[0]
    for a, n in re.findall(r'dc\.l\t\$([0-9a-f]+)\n\tdc\.w\t\$?([0-9a-f]+)', rr):
        a, n = int(a, 16), int(n, 16)
        if blk(a):
            foreign.update(range(a, a + 2 * (n + 1), 2))
    for b in blocks:
        bad = recipes[b.lo].touched & foreign
        if bad:
            raise ValueError('translation edits words the slave patches: ' + ' '.join(f'{a + D:05x}' for a in sorted(bad)))
    stubs, used = place(blocks, islands, 0x1000, 0x1a000)
    new_blocks = set(F5_BLOCKS)
    entries, slots = references(img, prog, blocks, blk, new_blocks)
    for e in entries:
        for f in entries:
            if e < f < e + 6:
                raise ValueError(f'entries overlap: {e + D:05x} {f + D:05x}')
    expmem, data_base = 0x200000, 0x240000
    base_of = lambda b: expmem + (0x1000 if b.dest == 'hot' else 0x1000 + 0x1000 + 0x7000 + 0x5000) + b.offset
    out = simulate(img, blocks, recipes, expmem, data_base)
    n = verify(img, blocks, out, newpos, growth, address_in, blk, base_of, data_base)
    words = write_table(blocks, recipes, thresholds, stubs, entries, slots, f2_operands)
    if args.check:
        check(args.check, img, blocks, recipes, stubs, newpos, address_in, blk, slots | set(f2_operands),
              entries)
    grow = sum(b.size - (b.hi - b.lo) for b in blocks)
    print(f'{len(blocks)} blocks, {sum(b.hi - b.lo for b in blocks)} bytes (+{grow}); '
          f'{len(growth)} rewrites, {len(widen)} widened branches; {n} instructions verified; '
          f'{len(stubs)} islands, {len(entries)} new entries, {len(slots)} new operands; '
          f'recipe {2 * words} bytes; hot {used["hot"]:#x}, render {used["render"]:#x}')
    for b in blocks:
        if b.dest == 'hot' and b.lo == M1_BLOCKS[0][0] and b.size != b.hi - b.lo:
            raise ValueError('M1 block 1 must not change (F4 patches it at fixed offsets)')
    if indirect:
        print('indirect jumps in blocks:', ' '.join(f'{p + D:05x}' for p in sorted(indirect)))


if __name__ == '__main__':
    main()
