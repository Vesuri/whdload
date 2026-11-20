#!/usr/bin/env python3
"""Recursive disassembly of the Virus image: every instruction reached from the entry and
the code pointers, and every operand that names a game address.

    python3 tools/relocmap.py [summary|refs|indirect|uncovered|dis ADDR [N]]

Reads Disk.1 (tmp/game/Virus/Disk.1) at its load address $3b800. Seeds: the entry, the
extra entries in SEEDS (code reached only through pointers the walk cannot follow), and
every absolute-long or immediate operand that points at an instruction start (iterated
until nothing new). The demo profile (tmp/prof/demo030/profile.pkl.gz) gives executed PCs
to check the walk against (`uncovered`: executed but not reached).
"""
import gzip
import pickle
import struct
import sys
from collections import defaultdict
from pathlib import Path

import capstone as cs
from capstone import m68k as M

ROOT = Path(__file__).resolve().parents[1]
BASE, SIZE = 0x3b800, 184320
END = BASE + SIZE
ENTRY = 0x63ec8
WORK = (0x1000, BASE)

CODE = (0x57000, 0x68800)    # code, with its own variables and tables: moves to fast memory

# Code entries no traced run executed, found by reading the gaps (tools/coverage.py).
SEEDS = {
    0x622c6: 'palette fade sequence (move.l #table,$1016; jsr $58e14 ...)',
    0x6356c: 'enemy behaviour, later waves (before $635a6)',
    0x63e00: 'object drawing helper (lea $1084,a1; jsr $604aa)',
    0x65b84: 'score digits (move.w d0,$65bc0; jsr $58cc6)',
    0x673de: 'object list drawing (movea.l (a5)+,a6; jsr $604aa)',
    0x62356: 'palette fade sequence, after the rts at $62354',
    0x623e8: 'palette fade sequence after the rts at $623e6; no reference found (dead?)',
    0x636b8: 'enemy state (lea $636b8,a4 at $6363a)',
    0x637fc: 'enemy state (lea $637fc,a4 at $664b8)',
    0x63982: 'enemy state (move.l #$63982,(a1) at $634dc)',
}

# Entries of code that traced runs executed (tools/coverage.py: the title, the attract
# screen, the demo, play to wave 4, game over, the highscore entry, a new game, pause), the
# fewest from which the walk reaches every executed PC: span writer entries, interrupt
# handlers, routines reached through registers. The walk needs no trace once these are here.
TRACED = (
    0x5788a, 0x57cfc, 0x58376, 0x58e26, 0x58e7e, 0x58eca, 0x592c2, 0x5931a,
    0x59366, 0x593c4, 0x59424, 0x5976a, 0x597c2, 0x5980e, 0x5986c, 0x598cc,
    0x59c12, 0x59c6a, 0x59cb6, 0x59d14, 0x5a0ba, 0x5a112, 0x5a15e, 0x5a1bc,
    0x5a21c, 0x5a562, 0x5a5ba, 0x5a606, 0x5a664, 0x5a6c4, 0x5aa0a, 0x5aa62,
    0x5aaae, 0x5ab0c, 0x5ab6c, 0x5aeb2, 0x5af0a, 0x5af56, 0x5b35a, 0x5b3b2,
    0x5b3fe, 0x5b802, 0x5b85a, 0x5b8a6, 0x5b904, 0x5b964, 0x5bcaa, 0x5bd02,
    0x5bd4e, 0x5c152, 0x5c1aa, 0x5c1f6, 0x5c254, 0x5c2b4, 0x5c5fa, 0x5c652,
    0x5c69e, 0x5caa2, 0x5cafa, 0x5cf4a, 0x5cfa2, 0x5cfee, 0x5d04c, 0x5d0ac,
    0x5d3f2, 0x5d442, 0x5d486, 0x5d870, 0x5d8de, 0x5dd86, 0x5ddf4, 0x5e29c,
    0x5e30a, 0x5e7b2, 0x5e820, 0x5e882, 0x5ecc8, 0x5ed36, 0x5ed98, 0x5ee0c,
    0x5f6f4, 0x5f762, 0x60180, 0x60740, 0x608a8, 0x60a52, 0x60ac2, 0x60b66,
    0x60c02, 0x60d22, 0x60dac, 0x60de0, 0x60e5a, 0x6103c, 0x610d6, 0x612ba,
    0x613ce, 0x61468, 0x6153c, 0x61568, 0x61716, 0x61786, 0x61832, 0x618a4,
    0x6192a, 0x627b2, 0x62894, 0x628fc, 0x62c26, 0x62e1e, 0x6735a, 0x67396,
    0x673aa, 0x67400,
)

# The slave's patches: traced PCs inside them are the patch's, not the game's.
PATCHED = ((0x608c0, 0x608c8), (0x644b6, 0x644c0), (0x67116, 0x6711e))

# Pointer tables in the image: (first, end, step); each long at first + k*step < end is a
# pointer (or 0). Code tables seed the walk.
CODE_TABLES = (
    (0x58c5a, 0x58c9a, 4),   # the dispatcher's states, lea $58c5a(pc) + 4*d0
    (0x60d02, 0x60d22, 4),   # object routine tables
    (0x60d9c, 0x60dac, 4),
    (0x613ae, 0x613ce, 4),
    (0x61458, 0x61468, 4),
    (0x614fc, 0x6153c, 4),
    (0x64a8c, 0x64acc, 4),   # particle plotters
)
DATA_TABLES = (
    (0x5813e, 0x5821e, 4),   # the 18-byte records at $57d4e
    (0x60120, 0x60180, 4),   # the span writers, entered at an offset from these
    (0x60636, 0x60652, 4),   # into the key table $60962
    (0x61de4, 0x61e24, 4),   # the waves' record lists
    (0x65550, 0x6556c, 4),   # the dot masks at $57848 / $57868 (and $4d970, below)
)
VARS = (
    0x58cb2,                 # the dispatcher's state, read with movea.l (pc)
)
# Uncovered bytes whose C-range longs are data that only look like addresses.
NOT_POINTERS = (
    (0x3b800, 0x57000, 'image data below the code: word records, bitmaps, font, samples'),
    (0x57000, 0x5788a, 'bitmaps, palettes, dot masks at the code area\'s start'),
    (0x57d4e, 0x5813e, 'the 18-byte records: words'),
    (0x61ba6, 0x61ba8, 'a wave record: the long $00000006 and $000004b0 straddled'),
)

AM = M.M68K_AM_ABSOLUTE_DATA_LONG, M.M68K_AM_ABSOLUTE_DATA_SHORT
EXT2 = {M.M68K_AM_ABSOLUTE_DATA_SHORT, M.M68K_AM_REGI_ADDR_DISP, M.M68K_AM_AREGI_INDEX_8_BIT_DISP,
        M.M68K_AM_AREGI_INDEX_BASE_DISP, M.M68K_AM_PCI_DISP, M.M68K_AM_PCI_INDEX_8_BIT_DISP,
        M.M68K_AM_PCI_INDEX_BASE_DISP}  # the 68000 has only the brief index format
PCIDX = (M.M68K_AM_PCI_INDEX_8_BIT_DISP, M.M68K_AM_PCI_INDEX_BASE_DISP)
QUICK = ('moveq', 'addq', 'subq', 'trap', 'lsl', 'lsr', 'asl', 'asr', 'rol', 'ror', 'roxl', 'roxr')
STOP = ('rts', 'rte', 'rtr', 'jmp', 'bra', 'illegal')


def image():
    return (ROOT / 'tmp/game/Virus/Disk.1').read_bytes()


class Insn:
    __slots__ = ('addr', 'size', 'mn', 'ops', 'text', 'targets', 'stop', 'abs', 'pcrel', 'indirect')


def decode(md, data, addr):
    """One instruction: its flow and its address operands (offset in the insn, value, kind)."""
    off = addr - BASE
    try:
        i = next(md.disasm(data[off:off + 10], addr, 1))
    except StopIteration:
        return None
    if i.mnemonic.startswith('.') or i.mnemonic in ('dc.w', 'invalid'):
        return None
    n = Insn()
    n.addr, n.size, n.mn, n.text = addr, i.size, i.mnemonic, f'{i.mnemonic} {i.op_str}'
    raw = data[off:off + i.size]
    base = n.mn.split('.')[0]
    sz = n.mn.split('.')[1] if '.' in n.mn else 'w'
    pos = 4 if base == 'movem' else 2
    n.abs, n.pcrel, n.targets, n.indirect = [], [], [], False
    for k, o in enumerate(i.operands):
        if o.type == M.M68K_OP_IMM:
            if base in QUICK:
                continue
            if base in ('btst', 'bchg', 'bclr', 'bset'):
                pos += 2
                continue
            if sz == 'l':
                v = struct.unpack('>I', raw[pos:pos + 4])[0]
                n.abs.append((pos, v, 'imm', k))
                pos += 4
            else:
                pos += 2
        elif o.type == M.M68K_OP_MEM:
            am = o.address_mode
            if am == M.M68K_AM_ABSOLUTE_DATA_LONG:
                v = struct.unpack('>I', raw[pos:pos + 4])[0]
                n.abs.append((pos, v, 'abs', k))
                pos += 4
            elif am == M.M68K_AM_ABSOLUTE_DATA_SHORT:
                v = struct.unpack('>h', raw[pos:pos + 2])[0] & 0xffffffff
                n.abs.append((pos, v, 'absw', k))
                pos += 2
            elif am == M.M68K_AM_PCI_DISP or am in PCIDX:
                d = struct.unpack('>h', raw[pos:pos + 2])[0] if am == M.M68K_AM_PCI_DISP \
                    else struct.unpack('>b', raw[pos + 1:pos + 2])[0]
                n.pcrel.append((pos, (addr + pos + d) & 0xffffffff, am in PCIDX, k))
                pos += 2
            elif am in EXT2:
                pos += 2
        elif o.type == M.M68K_OP_BR_DISP:
            n.targets.append((addr + 2 + o.br_disp.disp) & 0xffffffff)
            pos += 2 if base.startswith('db') or raw[1] == 0 else 0  # 68000: 8- or 16-bit
    if pos != n.size and base != 'movem' or base == 'movem' and pos > n.size:
        return None  # an encoding the 68000 does not have: not code
    n.stop = base in STOP
    if base in ('jmp', 'jsr'):
        a = [v for p, v, kind, _ in n.abs if kind in ('abs', 'absw')]
        p = [t for _, t, idx, _ in n.pcrel if not idx]
        if a or p:
            n.targets += a + p
        else:
            n.indirect = True
    n.ops = i.operands
    return n


def walk(data, seeds):
    md = cs.Cs(cs.CS_ARCH_M68K, cs.CS_MODE_BIG_ENDIAN | cs.CS_MODE_M68K_000)
    md.detail = True
    insns, todo, bad = {}, list(seeds), {}
    while todo:
        a = todo.pop()
        while BASE <= a < END and a not in insns and not a & 1:
            n = decode(md, data, a)
            if n is None:
                bad[a] = 'undecodable'
                break
            insns[a] = n
            for t in n.targets:
                if BASE <= t < END:
                    todo.append(t)
            if n.stop:
                break
            a += n.size
    return insns, bad


def analyse(data=None):
    data = data or image()
    seeds = {ENTRY} | set(SEEDS) | set(TRACED) | {v for v in table_values(data, code_slots(data)) if v}
    while True:
        insns, bad = walk(data, seeds)
        more = {v for n in insns.values() for _, v, kind, _ in n.abs
                if kind in ('abs', 'imm') and v in insns} - seeds
        # a code pointer to an instruction start already reached adds nothing; to anything
        # else in the image it is only a candidate (see `refs`)
        if not more:
            return insns, bad
        seeds |= more


WAVES = (0x61de4, 0x61e24)    # the waves' enemy lists, one pointer a wave


def long_at(data, x):
    return struct.unpack('>I', data[x - BASE:x - BASE + 4])[0]


def wave_slots(data):
    """The routine pointers in the waves' enemy lists: records of five longs (count, three
    values, routine), each list ended by a zero long."""
    out = set()
    for a in {long_at(data, x) for x in range(*WAVES, 4)}:
        while long_at(data, a):
            out.add(a + 16)
            a += 20
    return sorted(out)


def code_slots(data):
    return [x for first, end, step in CODE_TABLES for x in range(first, end, step)] + wave_slots(data)


def data_slots(data):
    return [x for first, end, step in DATA_TABLES for x in range(first, end, step)] + list(VARS)


def table_values(data, slots):
    return [long_at(data, x) for x in slots]


def starts(insns):
    """Every byte covered by an instruction, mapped to its start."""
    cover = {}
    for a, n in insns.items():
        for b in range(a, a + n.size):
            cover[b] = a
    return cover


def demo_pcs():
    """Executed PCs: tools/coverage.py's set, else the demo benchmark's profile."""
    cov = ROOT / 'tmp/re/coverage.pkl'
    if cov.exists():
        return set(pickle.load(open(cov, 'rb')))
    p = pickle.load(gzip.open(ROOT / 'tmp/prof/demo030/profile.pkl.gz'))
    return {k for k in p['self'] if isinstance(k, int) and BASE <= k < END}


def region(v):
    if WORK[0] <= v < WORK[1]:
        return 'work'
    if BASE <= v < END:
        return 'image'
    return None


def in_code(v):
    return CODE[0] <= v < CODE[1]


def relocations(data, insns):
    """The image addresses of every long that holds a code-area address: (addr, why)."""
    out = {}
    for a, n in insns.items():
        for p, v, kind, _ in n.abs:
            if kind in ('abs', 'imm') and in_code(v):
                out[a + p] = f'{kind} {n.text}'
    for x in code_slots(data) + data_slots(data):
        if in_code(long_at(data, x)):
            out[x] = 'table' if x not in VARS else 'variable'
    return out


def check(data, insns):
    """Problems: code-range longs in unreached bytes nobody accounted for, PC-relative
    operands leaving the code area, instructions outside it."""
    cover = starts(insns)
    known = set(code_slots(data) + data_slots(data))
    bad = []
    for x in range(BASE, END - 3, 2):
        if x in cover or x in known or any(lo <= x < hi for lo, hi, _ in NOT_POINTERS):
            continue
        v = struct.unpack('>I', data[x - BASE:x - BASE + 4])[0]
        if in_code(v):
            bad.append(f'{x:x} ({x - BASE:x}): unexplained {v:x}')
    owner = {}
    for a, n in sorted(insns.items()):
        for x in range(a, a + n.size):
            if x in owner:
                bad.append(f'{a:x}: overlaps the instruction at {owner[x]:x}')
                break
            owner[x] = a
    try:
        miss = demo_pcs() - set(insns)
        bad += [f'{a:x}: executed (tools/coverage.py) but not reached' for a in sorted(miss)
                if not any(lo <= a < hi for lo, hi in PATCHED)]
    except FileNotFoundError:
        pass
    for a, n in sorted(insns.items()):
        if not in_code(a):
            bad.append(f'{a:x}: instruction outside the code area: {n.text}')
        for p, t, idx, _ in n.pcrel:
            if not in_code(t):
                bad.append(f'{a:x}: PC-relative operand leaves the code area: {n.text}')
    return bad


def main(args):
    cmd = args[0] if args else 'summary'
    data = image()
    insns, bad = analyse(data)
    cover = starts(insns)
    if cmd == 'summary':
        code = sum(n.size for n in insns.values())
        print(f'{len(insns)} instructions, {code} bytes, {len(bad)} undecodable stops')
        kinds = defaultdict(int)
        for n in insns.values():
            for _, v, kind, _ in n.abs:
                r = region(v)
                if r:
                    tgt = 'code' if v in insns else ('in-insn' if v in cover else 'data')
                    kinds[(kind, r, tgt if r == 'image' else '')] += 1
        for k in sorted(kinds):
            print(f'  {k[0]:4} -> {k[1]:5} {k[2]:8} {kinds[k]}')
        print(f'  indirect jumps {sum(n.indirect for n in insns.values())}, '
              f'PC-relative operands {sum(len(n.pcrel) for n in insns.values())}')
        try:
            pcs = demo_pcs()
            miss = pcs - set(insns)
            print(f'demo PCs {len(pcs)}, not reached by the walk {len(miss)}')
        except FileNotFoundError:
            pass
        for a, why in sorted(bad.items()):
            print(f'  stop {a:x} ({a - BASE:x}): {why}')
    elif cmd == 'refs':
        for a in sorted(insns):
            n = insns[a]
            for p, v, kind, _ in n.abs:
                r = region(v)
                if r:
                    tgt = 'code' if v in insns else ('in-insn' if v in cover else 'data')
                    print(f'{a:x} +{p} {kind:4} {v:6x} {r:5} {tgt if r == "image" else "":7} {n.text}')
    elif cmd == 'check':
        bad = check(data, insns)
        print('\n'.join(bad) or 'ok')
        sys.exit(1 if bad else 0)
    elif cmd == 'inc':
        bad = check(data, insns)
        if bad:
            sys.exit('check fails:\n' + '\n'.join(bad))
        locs = sorted(relocations(data, insns))
        assert all(not x & 1 and in_code(x) for x in locs)
        out = [f'; Generated by tools/relocmap.py inc: the {len(locs)} longs in the code area',
               f'; (${CODE[0]:x}-${CODE[1] - 1:x}) that hold a code-area address, as (address - ${CODE[0]:x}) / 2.',
               f'RELOC_COUNT\t= {len(locs)}', '_reloc']
        for k in range(0, len(locs), 12):
            out.append('\tdc.w\t' + ','.join(f'${(x - CODE[0]) // 2:04x}' for x in locs[k:k + 12]))
        (ROOT / 'src/reloc.i').write_text('\n'.join(out) + '\n')
        print(f'src/reloc.i: {len(locs)} relocations')
    elif cmd == 'imm':
        for a in sorted(insns):
            for p, v, kind, _ in insns[a].abs:
                if kind == 'imm' and in_code(v):
                    print(f'{a:x} ({a - BASE:x}) {insns[a].text}')
    elif cmd == 'indirect':
        for a in sorted(insns):
            if insns[a].indirect:
                print(f'{a:x} ({a - BASE:x}) {insns[a].text}')
    elif cmd == 'uncovered':
        miss = sorted(demo_pcs() - set(insns))
        prev = None
        for a in miss:
            if prev is None or a - prev > 16:
                print(f'{a:x} ({a - BASE:x})')
            prev = a
    elif cmd == 'dis':
        a, cnt = int(args[1], 16), int(args[2]) if len(args) > 2 else 20
        md = cs.Cs(cs.CS_ARCH_M68K, cs.CS_MODE_BIG_ENDIAN | cs.CS_MODE_M68K_000)
        md.detail = True
        for _ in range(cnt):
            n = decode(md, data, a)
            if n is None:
                print(f'{a:x}: ??')
                break
            print(f'{a:x}{"*" if a in insns else " "} {n.text}')
            a += n.size


if __name__ == '__main__':
    main(sys.argv[1:])
