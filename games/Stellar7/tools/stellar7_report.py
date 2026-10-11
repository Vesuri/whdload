#!/usr/bin/env python3
"""Attribute cycle-exact Stellar 7 traces to loaded hunks and routines.

python3 tools/stellar7_report.py TRACE MEMDUMP --base 0xc00000
Reused from Their Finest Hour. Hunk locations are validated against the
startup's relocated A4; the data hunk follows LoadSeg's BPTR chain.
Aztec C link-a5 prologues and observed call targets name functions.
"""
import argparse, collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import barto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def locate(mem, blob, base, step=64, header=0x28):
    votes = collections.Counter()
    for off in range(0, len(blob) - 16, step):
        w = blob[off:off + 16]
        if w.count(0) > 8:
            continue
        # Vote for every occurrence (up to 4): WHDLoad's PRELOAD cache can hold a second copy.
        i, seen = mem.find(w), 0
        while i >= 0 and seen < 4:
            votes[base + i - off] += 1
            i, seen = mem.find(w, i + 1), seen + 1
    # WHDLoad's PRELOAD caches whole files in memory: a copy preceded by its own hunk header
    # ($3F3 at file offset 0, `header` bytes before the hunk) is the cached file, not the
    # loaded program.
    for a, n in votes.most_common():
        hdr = a - base - header
        if a >= base and n >= max(4, len(blob)//step//3) and not (hdr >= 0 and mem[hdr:hdr + 4] == b'\0\0\x03\xf3'):
            return a
    return None


GAME = os.path.join(ROOT, 'tmp/game/Stellar7NTSC/data/s7')
KICK13 = os.environ.get('KICK13') or os.path.expanduser('~/.local/share/amiga/Kickstarts/kick34005.A500')
CODE_FILE, CODE_SIZE, DATA_SIZE = 0x24, 0x25360, 0x823c



def loaded_game_regions(dump, base, chip=None):
    """Find this supplied game's loaded hunk without scanning ROM/slave images.

    The unpatched entry prefix identifies candidates; the relocated A4 and DOS
    next-segment link must agree on the data hunk. Preload file copies fail that
    relocation check. Used only for startup detection, not patch validation.
    """
    prefix = open(GAME, 'rb').read()[CODE_FILE:CODE_FILE+12]
    candidates = []
    for memory, origin in [(dump, base)] + ([(chip, 0)] if chip is not None else []):
        offset = memory.find(prefix)
        while offset >= 0:
            if offset >= 4 and offset+CODE_SIZE <= len(memory):
                data = struct.unpack_from('>I', memory, offset-4)[0]*4+4
                a4 = struct.unpack_from('>I', memory, offset+14)[0]
                if a4 == data+0x8000 and any(
                        start <= data and data+DATA_SIZE <= start+len(blob)
                        for blob, start in [(dump, base)] + ([(chip, 0)] if chip is not None else [])):
                    address = origin+offset
                    candidates.append([(address, address+CODE_SIZE, 's7', address),
                                       (data, data+DATA_SIZE, 's7-data', data)])
            offset = memory.find(prefix, offset+1)
    if len(candidates) != 1:
        raise ValueError(f'Expected one relocated game hunk, found {len(candidates)}')
    return candidates[0]


def regions(dump, base, chip=None):
    game = open(GAME, 'rb').read()
    code = game[CODE_FILE:CODE_FILE + CODE_SIZE]
    mems = [(dump, base)] + ([(chip, 0)] if chip is not None else [])
    out = []
    for mem, mbase in mems:
        a = locate(mem, code, mbase, header=CODE_FILE)
        if a is not None:
            # Startup's relocated A4 must point into the loaded data hunk.
            at = a-mbase
            data = struct.unpack_from('>I', mem, at-4)[0]*4+4
            a4 = struct.unpack_from('>I', mem, at+14)[0]
            if a4 != data+0x8000:
                continue
            out.append((a, a+CODE_SIZE, 's7', a))
            out.append((data, data+DATA_SIZE, 's7-data', data))
            break
    for mem, mbase in mems:
        a = locate(mem, open(KICK13, 'rb').read(), mbase, 256)
        if a is not None:
            out.append((a,a+0x40000,'kick',a-0xfc0000)); break
    slave_path = os.environ.get('SLAVE') or os.path.join(ROOT,'tmp/game/Stellar7NTSC/Stellar7NTSC.Slave')
    slave = open(slave_path,'rb').read()
    size = struct.unpack_from('>I',slave,0x1c)[0]*4
    shunk=slave[0x20:0x20+size]
    for mem, mbase in mems:
        a=locate(mem,shunk,mbase,16,0x20)
        if a is not None:
            out.append((a,a+size,'slave',a));break
    if not any(r[2]=='s7' for r in out):
        raise ValueError('Loaded s7 not found; capture after LoadSeg, with the matching memory dump')
    return out


class Namer:
    def __init__(self, regs, mem):
        self.regs, self.mem = regs, mem
        self.libs = {}
        self.starts = set()
        for lo, hi, name, origin in regs:
            if name == 's7':
                for a in range(lo, hi, 2):
                    if mem.word(a) == 0x4e55:  # link a5,#n: Aztec C prologue
                        self.starts.add(a)

    def addr(self, pc):
        if pc is None:
            return '[missing PC]'
        if pc == 0x7fffffff:
            return '[between-instruction gap]'
        for lo, hi, name, origin in self.regs:
            if lo <= pc < hi:
                return f'{name}:{pc - origin:05x}' if name != 'kick' else f'kick:{pc - origin:06x}'
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
    pending = {}  # context -> (sp_before, label) for its last executed call
    starts = set(namer.starts)
    for f in fields:
        for pc, cost, r in trace.instructions(f):
            sp = r[15]
            sup = ctx_of(sp)  # execution context = which stack SP lies in
            if pc is None or pc == 0x7fffffff:
                kinds['missing-pc' if pc is None else 'between-instruction-gap'] += cost
                self_c[namer.addr(pc)] += cost
                incl[namer.addr(pc)] += cost
                continue
            st = stacks[sup]
            # Interrupts can occur between a call and its first instruction.
            # Retain that call until the same stack context resumes.
            waiting = pending.pop(sup, None)
            if waiting is not None:
                psp, plabel = waiting
                if sp == psp - 4:
                    # Keep the original entry as a range boundary even when
                    # its prologue was replaced by a jump. A trampoline can
                    # later execute that routine's native continuation; without
                    # this boundary its self time leaks into the preceding one.
                    starts.add(pc)
                    target = pc
                    if mem.word(pc) == 0x4ef9:  # jmp abs.l trampoline (jump table)
                        target = mem.long(pc + 2)
                    starts.add(target)
                    st.append((psp, plabel or namer.addr(target)))
                    calls[st[-1][1]] += 1
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
                pending[sup] = (sp, label)
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
    p.add_argument('--base', type=lambda s: int(s, 0), default=0x330000)
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
    recorded_cycles = sum(f.cycles for f in fields)
    print(f'# {a.trace}: {nf} fields, {total} cycles ({total / recorded_cycles:.3f} of recorded field cycles)')
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
