#!/usr/bin/env python3
"""Attribute a cycle-exact FS-UAE trace of the original Indianapolis 500 to its routines.

  python3 tools/i500_report.py TRACE.bin MEMDUMP.bin [--base=0xc00000] [--top=40]

TRACE is `i500.py profile` output (Barto format, all PCs recorded); MEMDUMP is a gdb
`dump binary memory` of the "other" memory (base address --base), taken in the same session
so the loaded addresses match; chip RAM comes from the trace's own snapshot.  Regions are
identified by matching memory against the installed files: the game's hunk executable stored
on Disk.1 (hunk 0 = `game`, the code), the intro loaded at 0, and the WHDLoad slave.

Calls are rebuilt from the instruction stream: a jsr/bsr pushes a frame (callee = the next
traced PC), the frame pops once SP climbs back above its return slot.  `jsr d16(a6)` is
named after the library node at a6 and the LVO.  User and supervisor execution keep
separate stacks.  Cycles are 7.09 MHz CPU clocks; a PAL field is 142,102.
"""
import argparse, collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev  # noqa: F401
from amigaxdev import barto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELD = 142102


class Memory:
    def __init__(self, trace, dump, base):
        self.chip, self.dump, self.base = trace.chip, dump, base

    def read(self, a, n):
        if self.base <= a and a + n <= self.base + len(self.dump):
            return self.dump[a - self.base:a - self.base + n]
        if a + n <= len(self.chip):
            return self.chip[a:a + n]
        return None

    def word(self, a):
        b = self.read(a, 2)
        return struct.unpack('>H', b)[0] if b else None

    def long(self, a):
        b = self.read(a, 4)
        return struct.unpack('>I', b)[0] if b else None

    def cstr(self, a):
        out = b''
        while a and len(out) < 40:
            b = self.read(a, 1)
            if not b or b == b'\0':
                break
            out += b
            a += 1
        return out.decode('latin1')


def locate(mem, blob, base, step=64, skip=None):
    """Return the address where blob sits in mem (dumped at base), by 16-byte window votes.
    skip(addr) rejects a candidate (e.g. a cached file copy)."""
    # Seed candidates with evenly spread windows, then score them using every
    # window. Loaded hunks retain thousands of immutable windows; searching
    # the entire RAM dump for each one made calibration take over a minute.
    offsets = list(range(0, len(blob) - 16, step))
    seeds = offsets[::max(1, len(offsets) // 128)]
    candidates = set()
    for off in seeds:
        w = blob[off:off + 16]
        if w.count(0) > 8:
            continue
        i, seen = mem.find(w), 0
        while i >= 0 and seen < 4:
            a = base + i - off
            if not (skip and skip(a)):
                candidates.add(a)
            i, seen = mem.find(w, i + 1), seen + 1
    scores = collections.Counter()
    for a in candidates:
        for off in offsets:
            w = blob[off:off + 16]
            i = a - base + off
            if w.count(0) <= 8 and i >= 0 and mem[i:i + 16] == w:
                scores[a] += 1
    if scores and scores.most_common(1)[0][1] >= 4:
        return scores.most_common(1)[0][0]
    # Sparse or heavily rewritten blobs retain the exhaustive fallback.
    votes = collections.Counter()
    for off in offsets:
        w = blob[off:off + 16]
        if w.count(0) > 8:
            continue
        # Vote for every occurrence (up to 4): WHDLoad's PRELOAD cache can hold a second copy.
        i, seen = mem.find(w), 0
        while i >= 0 and seen < 4:
            votes[base + i - off] += 1
            i, seen = mem.find(w, i + 1), seen + 1
    for a, n in votes.most_common():
        if n >= 4 and not (skip and skip(a)):
            return a
    return None


GAME = os.path.join(ROOT, 'tmp/game/Indianapolis500')
DISK = os.path.join(GAME, 'Disk.1')
EXE_OFFSET = 0x1a200  # the game is an AmigaDOS hunk executable stored raw at this Disk.1 offset
INTRO_SIZE = 19 * 0x1600  # the slave DiskLoads this much to address 0 and jumps to $a040


def game_hunks(disk=None):
    """Parse the hunk executable on Disk.1: [(index, kind, file offset or None, size, memflags)]."""
    disk = disk or open(DISK, 'rb').read()
    off = EXE_OFFSET
    def L():
        nonlocal off
        v = struct.unpack_from('>I', disk, off)[0]; off += 4; return v
    assert L() == 0x3f3 and L() == 0
    L(); first, last = L(), L()
    sizes = [L() for _ in range(last - first + 1)]
    out = []
    while len(out) < len(sizes):
        t = L() & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            n = (L() & 0x3fffffff) * 4
            out.append((len(out), 'code' if t == 0x3e9 else 'data', off, n, sizes[len(out)] >> 30))
            off += n
        elif t == 0x3eb:
            out.append((len(out), 'bss', None, (L() & 0x3fffffff) * 4, sizes[len(out)] >> 30))
        elif t == 0x3ec:
            while (c := L()):
                L(); off += 4 * c
        elif t != 0x3f2:
            # Hunk 4's DATA block on Disk.1 is followed by $404 bytes before its HUNK_END
            # (the file was written with slack); resynchronise on the next HUNK_END.
            k = disk.find(b'\0\0\x03\xf2', off - 4, off + 0x1000)
            if k >= 0 and k % 2 == 0:
                off = k + 4
                continue
            raise ValueError(f'hunk type {t:#x} at Disk.1+{off - 4:#x}')
    return out


def regions(dump, base, chip=None):
    """(lo, hi, name, origin) for every code/data region found in dump (and chip, if given).
    Names: game = hunk 0 (the code; offsets are the slave's PL_GAME numbering), hunkN = other
    file-backed hunks, intro = the boot code the slave loads at 0, slave = the WHDLoad slave."""
    disk = open(DISK, 'rb').read()
    slave_path = os.environ.get('SLAVE', 'original')
    if slave_path == 'original':  # common/run.sh's name for the installed slave
        slave_path = os.path.join(GAME, 'Indianapolis500.Slave')
    slave = open(slave_path, 'rb').read()
    mems = [(dump, base)] + ([(chip, 0)] if chip is not None else [])
    out = []
    for i, kind, foff, size, flags in game_hunks(disk):
        if foff is None:
            continue
        blob = disk[foff:foff + size]
        for mem, mbase in mems:
            # The PRELOAD copy of Disk.1 is in memory too: the real hunk is not preceded by
            # the bytes that precede it on disk.
            def cached(a, mem=mem, mbase=mbase, foff=foff, i=i):
                o = a - mbase
                if o >= 16 and mem[o - 16:o] == disk[foff - 16:foff]:
                    return True
                if i == 0:
                    # Four window votes can occur in unrelated preload memory.
                    # A tick load no patch touches (game:26d24 move.w game:9832,game:26662)
                    # must be live and relocated to this candidate's own hunk, not raw file
                    # offsets or random data. (game:00152 is hooked by the motion patches.)
                    if o < 0 or o + 0x26d2e > len(mem): return True
                    if mem[o+0x26d24:o+0x26d26] != b'\x33\xf9': return True
                    if struct.unpack_from('>I',mem,o+0x26d26)[0] != a+0x9832: return True
                return False
            a = locate(mem, blob, mbase, skip=cached)
            if a is not None:
                out.append((a, a + size, 'game' if i == 0 else f'hunk{i}', a))
                break
    if chip is not None:
        a = locate(chip, disk[:INTRO_SIZE], 0, 256)
        if a is not None:
            out.append((a, a + INTRO_SIZE, 'intro', a))
    # The slave is the copy WHDLoad runs: its resload pointer (hunk offset $a0, just before
    # loader) is filled in. Derive the loader offset from ws_GameLoader because
    # configuration strings change the header layout. Match immutable loader code;
    # private option tags later in the slave change at runtime.
    code = slave[0x20:0x20 + 4 * struct.unpack_from('>I', slave, 0x14)[0]]  # one-hunk slave
    entry = struct.unpack_from('>H', code, 24)[0]
    signature = code[entry:entry + 128]
    i = dump.find(signature)
    while i >= 0:
        h = i - entry
        if h >= 0 and dump[h + entry - 4:h + entry] != b'\0\0\0\0':
            out.append((base + h, base + h + len(code), 'slave', base + h))
            break
        i = dump.find(signature, i + 1)
    return out


class Namer:
    def __init__(self, regs, mem):
        self.regs, self.mem = regs, mem
        self.libs = {}
        self.starts = set()
        # Hand-written asm: no prologues.  Function starts are every static call target in
        # the game code (jsr abs.l after relocation, bsr.b/.w) plus the calls seen in the trace.
        for lo, hi, name, origin in regs:
            if name == 'game':
                for a in range(lo, hi - 4, 2):
                    w = mem.word(a)
                    if w == 0x4eb9:
                        t = mem.long(a + 2)
                        if lo <= t < hi:
                            self.starts.add(t)
                    elif (w & 0xff00) == 0x6100:
                        d = w & 0xff
                        t = a + 2 + (struct.unpack('>h', mem.read(a + 2, 2))[0] if d == 0 else (d - 256 if d > 127 else d))
                        if lo <= t < hi:
                            self.starts.add(t)

    def addr(self, pc):
        if pc is None:
            return '[stopped]'
        if pc == 0x7fffffff:
            return '[irq entry]'
        for lo, hi, name, origin in self.regs:
            if lo <= pc < hi:
                return f'{name}:{pc - origin:05x}'
        if pc >= 0xf80000:
            return f'rom:{pc:06x}'
        return f'?{pc:06x}'

    def lib(self, base):
        if base not in self.libs:
            name = self.mem.cstr(self.mem.long(base + 10) or 0)
            self.libs[base] = name.replace('.library', '').replace('.resource', '') or f'lib@{base:x}'
        return self.libs[base]


def contexts(trace, fields):
    """Group stack pointers into stacks: pages closer than 8 KB belong to one stack.
    UAE's recorded SR is stale (rebuilt lazily), so SP is the only mode signal."""
    pages = collections.Counter()
    for f in fields[:10]:
        for pc, cost, r in trace.instructions(f):
            pages[r[15] >> 12] += cost
    groups, cur = [], []
    for p in sorted(pages):
        if cur and p - cur[-1] > 2:
            groups.append(cur); cur = []
        cur.append(p)
    if cur: groups.append(cur)
    groups.sort(key=lambda g: -sum(pages[p] for p in g))
    return [(g[0] << 12, (g[-1] + 1) << 12) for g in groups]


def analyse(trace, mem, namer, fields):
    ranges = contexts(trace, fields)
    labels = ['main'] + [f'ctx{i}' for i in range(1, len(ranges))]
    def ctx_of(sp):
        for (lo, hi), name in zip(ranges, labels):
            if lo <= sp < hi + 0x1000:
                return f'{name}@{lo:x}'
        return f'sp@{sp >> 12:x}000'
    self_c = collections.Counter()
    incl = collections.Counter()
    calls = collections.Counter()
    edges = collections.Counter()  # (caller, callee) -> inclusive cycles
    pcs = collections.Counter()
    leafpcs = collections.Counter()
    kinds = collections.Counter()
    stacks = collections.defaultdict(list)  # context -> [(sp_before, name)]
    pending = None  # (sp_before, label or None) for the call just executed
    starts = set(namer.starts)
    for f in fields:
        for pc, cost, r in trace.instructions(f):
            sp = r[15]
            sup = ctx_of(sp)  # execution context = which stack SP lies in
            if pc is None or pc == 0x7fffffff:
                kinds['stopped' if pc is None else 'irq-entry'] += cost
                self_c[namer.addr(pc)] += cost
                incl[namer.addr(pc)] += cost
                pending = None
                continue
            st = stacks[sup]
            if pending is not None:
                psp, plabel, psup = pending
                if psup == sup and sp == psp - 4:
                    target = pc
                    if mem.word(pc) == 0x4ef9:  # jmp abs.l trampoline (jump table)
                        target = mem.long(pc + 2)
                    starts.add(target)
                    st.append((psp, plabel or namer.addr(target)))
                    calls[st[-1][1]] += 1
                pending = None
            while st and sp >= st[-1][0]:
                st.pop()
            if len(st) > 200:
                del st[:100]
            leafpcs[(sup, pc)] += cost
            seen = set()
            prev = '[top]'
            for _, name in st:
                if name not in seen:
                    incl[name] += cost
                    seen.add(name)
                edges[(prev, name)] += cost
                prev = name
            pcs[pc] += cost
            kinds[sup] += cost
            op = mem.word(pc)
            if op is None:
                continue
            if (op & 0xff00) == 0x6100 or (op & 0xffc0) == 0x4e80:
                label = None
                if op == 0x4eae:  # jsr d16(a6)
                    disp = struct.unpack('>h', mem.read(pc + 2, 2))[0]
                    label = f'{namer.lib(r[14])}{disp}'
                pending = (sp, label, sup)
    ordered = sorted(starts)
    import bisect
    by_ctx = collections.defaultdict(collections.Counter)
    for (ctx, pc), c in leafpcs.items():
        i = bisect.bisect_right(ordered, pc) - 1
        fn = ordered[i] if i >= 0 else None
        name = namer.addr(fn) if fn is not None and namer.addr(fn).split(':')[0] == namer.addr(pc).split(':')[0] else namer.addr(pc)
        self_c[name] += c
        by_ctx[ctx][name] += c
    return self_c, incl, calls, edges, pcs, kinds, by_ctx


def main():
    p = argparse.ArgumentParser()
    p.add_argument('trace')
    p.add_argument('dump')
    p.add_argument('--base', type=lambda s: int(s, 0), default=0xc00000)
    p.add_argument('--top', type=int, default=40)
    p.add_argument('--fields', default=None, help='a-b (0-based, inclusive)')
    a = p.parse_args()
    trace = barto.load(a.trace)
    dump = open(a.dump, 'rb').read()
    mem = Memory(trace, dump, a.base)
    regs = regions(dump, a.base, trace.chip)
    namer = Namer(regs, mem)
    fields = trace.fields
    if a.fields:
        lo, hi = map(int, a.fields.split('-'))
        fields = fields[lo:hi + 1]
    self_c, incl, calls, edges, pcs, kinds, by_ctx = analyse(trace, mem, namer, fields)
    total = sum(kinds.values())
    nf = len(fields)
    print(f'# {a.trace}: {nf} fields, {total} cycles ({total / nf / FIELD:.3f} of each field)')
    print('regions:', ', '.join(f'{n} {lo:#x}-{hi:#x}' for lo, hi, n, _ in regs))
    print('by mode:', ', '.join(f'{k} {100 * v / total:.1f}%' for k, v in kinds.most_common()))
    reg = collections.Counter()
    for pc, c in pcs.items():
        reg[namer.addr(pc).split(':')[0]] += c
    print('by region:', ', '.join(f'{k} {100 * v / total:.1f}%' for k, v in reg.most_common()))
    for ctx, cnt in sorted(by_ctx.items(), key=lambda kv: -sum(kv[1].values())):
        ct = sum(cnt.values())
        print(f'\n## Context {ctx}: {100 * ct / total:.1f}% ({ct / nf:.0f} cycles/field), self time')
        for name, c in cnt.most_common(12):
            print(f'{100 * c / total:6.2f} {c / nf:9.0f}  {name}')
    print(f'\n## Self time (top {a.top})')
    print(f'{"%":>6} {"cyc/field":>9} {"calls":>7}  routine')
    for name, c in self_c.most_common(a.top):
        print(f'{100 * c / total:6.2f} {c / nf:9.0f} {calls[name]:7d}  {name}')
    print(f'\n## Inclusive time (top {a.top})')
    print(f'{"%":>6} {"cyc/field":>9} {"calls":>7} {"cyc/call":>8}  routine')
    for name, c in incl.most_common(a.top):
        n = calls[name]
        print(f'{100 * c / total:6.2f} {c / nf:9.0f} {n:7d} {c / n if n else 0:8.0f}  {name}')
    print(f'\n## Hottest instructions')
    for pc, c in pcs.most_common(25):
        op = mem.read(pc, 6)
        print(f'{100 * c / total:6.2f}  {pc:06x} {namer.addr(pc):16s} {op.hex() if op else ""}')
    print(f'\n## Call edges (inclusive cycles, top 40)')
    for (x, y), c in edges.most_common(40):
        print(f'{100 * c / total:6.2f}  {x} -> {y}')


if __name__ == '__main__':
    main()
