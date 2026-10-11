#!/usr/bin/env python3
"""Attribute a cycle-exact FS-UAE trace of the original Powerdrome to its routines.

  python3 tools/powerdrome_report.py TRACE.bin MEMDUMP.bin [--base=0xc00000] [--top=40]

TRACE is `powerdrome.py profile` output (Barto format, all PCs recorded); MEMDUMP is a gdb
`dump binary memory` of the "other" memory (base address --base), taken in the same session
so the loaded addresses match; chip RAM comes from the trace's own snapshot.  Regions are
identified by matching the relocated single-hunk pd executable, the resident original slave,
and its patched Kickstart 1.3 image. The game is extracted from Disk.1 in memory.
The resident slave is identified through its loader and initialized resload pointer.

Calls are rebuilt from the instruction stream: a jsr/bsr pushes a frame (callee = the next
traced PC), the frame pops once SP climbs back above its return slot.  `jsr d16(a6)` is
named after the library node at a6 and the LVO.  User and supervisor execution keep
separate stacks.  Cycles are 7.09 MHz CPU clocks; a PAL field is 142,102.
"""
import argparse, collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev
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


GAME = os.path.join(ROOT, 'tmp/game/Powerdrome')


def game_code():
    from amigaxdev import adf
    disk = open(os.path.join(GAME, 'Disk.1'), 'rb').read()
    hdr = next(h for p, h, n in adf.walk(disk) if p.lower() == 'pd')
    exe = adf.read(disk, hdr)
    size = struct.unpack_from('>I', exe, 28)[0] * 4
    return exe[32:32 + size]


def regions(dump, base, chip=None):
    from amigaxdev.patchlist import slave_code
    out = []
    blob = game_code()
    slave = slave_code(os.environ.get('SLAVE') or os.path.join(GAME, 'Powerdrome.Slave'))
    for mem, mbase in [(dump, base)] + ([(chip, 0)] if chip is not None else []):
        def cached(a):
            i = a - mbase
            # A relocated executable begins with a jump to its own entry.
            return i < 4 or i + len(blob) > len(mem) or mem[i:i+2] != b'\x4e\xf9' or int.from_bytes(mem[i+2:i+6], 'big') != a + 0x4fc0
        addr = locate(mem, blob, mbase, skip=cached)
        if addr is not None:
            out.append((addr, addr + len(blob), 'game', addr))
        entry = int.from_bytes(slave[24:26], 'big')
        if slave[entry:entry+2] == b'\x60\x00':
            entry += 2 + int.from_bytes(slave[entry+2:entry+4], 'big', signed=True)
        if slave[entry:entry+2] != b'\x43\xfa':
            raise ValueError('unknown slave loader signature')
        resptr = entry + 2 + int.from_bytes(slave[entry+2:entry+4], 'big', signed=True)
        sig = slave[entry:entry+64]
        i = mem.find(sig)
        while i >= 0:
            start = i - entry
            if start >= 0 and any(mem[start+resptr:start+resptr+4]):
                a = mbase + start
                out.append((a, a + len(slave), 'slave', a))
                break
            i = mem.find(sig, i+1)
    # Original LoadKick relocates a patched Kickstart image into expansion memory.
    kickpath = os.environ.get('KICK13', os.path.expanduser('~/.local/share/amiga/Kickstarts/kick34005.A500'))
    kick = open(kickpath, 'rb').read()
    addr = locate(dump, kick, base, step=256, skip=lambda a: a < base or a+len(kick)>base+len(dump))
    if addr is not None: out.append((addr, addr+len(kick), 'kick', addr))
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
            return f'host-rom:{pc - 0xf80000:05x}'
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
    print(f'# {a.trace}: {nf} fields, {total} recorded cycles ({total / nf:.0f} per field; CPU-backend scale)')
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
