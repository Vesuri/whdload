#!/usr/bin/env python3
"""Attribute a cycle-exact FS-UAE trace of the original Grand Prix Circuit to its routines.

  python3 tools/gpc_report.py TRACE.bin MEMDUMP.bin [--base=0x330000] [--top=40]

TRACE is `gpc.py profile` output (Barto format, all PCs recorded); MEMDUMP is a gdb
`dump binary memory` of the region holding the code (base address --base), taken in the
same session so the loaded addresses match.  Code regions are identified by matching the
dump against the installed files: `gpc` root code hunk, the Kickstart 1.3 image kickemu
copies into RAM, and the WHDLoad slave.

Calls are rebuilt from the instruction stream: a jsr/bsr pushes a frame (callee = the next
traced PC), the frame pops once SP climbs back above its return slot.  `jsr d16(a6)` is
named after the library node at a6 and the LVO.  User and supervisor execution keep
separate stacks.  Cycles are 7.09 MHz CPU clocks; a PAL field is 142,102.
"""
import argparse, collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from amigaxdev.env import path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELD = 142102
LABELS = {
 0x372:'swap_views',0x729a:'draw_scene',0x772a:'simulation_VBL',0x776a:'step_state',
 0x782e:'player_step',0x8010:'post_player_step',0x818c:'road_renderer',
 0x82ea:'road_span_builder',0x83e6:'road_rows',0x883e:'span_wrapper',0x8864:'four_plane_span_fill',
 0x8a2a:'road_edge_lines',0x906a:'scene_objects',0x9a48:'scene_geometry',
 0x9ade:'object_projection',0x9d0c:'object_attribute_worker',0xa288:'AI_step',
 0xa58c:'frame_prepare',0xa6ea:'latch_state',0xa77c:'view_transform',0xa8ee:'frame_swap',
 0xb126:'audio_VBL',0xc11e:'RNG',0xc1da:'joystick_decode',0xc7f4:'shape_blitter',
 0xc9ca:'shape_cache_and_blit',0xcce2:'clipped_rectangle_fill',0xce1e:'movem_clear',
 0xcf8e:'wait_blitter_then_disown',0xcfd2:'line_drawer',0x6dc4:'dashboard',0x6e3e:'dashboard_values',0x6e64:'dashboard_text',
 0x6ae0:'car_cockpit_overlay',0x6a28:'cockpit_indicators',
}


KICK_LABELS = {0xfc08e6:'exec_interrupt_dispatch',0xfc08f6:'exec_interrupt_dispatch',
               0xfc8038:'graphics_raster_worker',0xfc6d48:'graphics_VBL'}

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


def locate(mem, blob, base, step=64):
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
    # ($3F3 at file offset 0) is the cached file, not the loaded program.
    for a, n in votes.most_common():
        hdr = a - base - 0x28
        if n >= 4 and not (hdr >= 0 and mem[hdr:hdr + 4] == b'\0\0\x03\xf3'):
            return a
    return None


def regions(dump, base):
    game = os.environ.get('GPC_GAME') or os.path.join(ROOT, 'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit')
    gpc = open(os.path.join(game, 'data/GrandPrixCircuit'), 'rb').read()
    kick = open(path('KICKSTART13'), 'rb').read()
    slave_path = os.environ.get('SLAVE') or os.path.join(ROOT, 'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/GrandPrixCircuit.Slave')
    slave = open(slave_path, 'rb').read()
    out = []
    code = gpc[0x28:0x28 + 0xe544]  # root code hunk (hunk 0)
    a = locate(dump, code, base)
    if a:
        out.append((a, a + len(code), 'gpc', a))
        # Follow LoadSeg's BPTR chain; a byte search can select the PRELOAD data copy.
        next_bptr = struct.unpack_from('>I', dump, a - base - 4)[0]
        data_base = next_bptr * 4 + 4
        if base <= data_base and data_base + 0x9364 <= base + len(dump):
            out.append((data_base, data_base + 0x9364, 'gpc-data', data_base))
    a = locate(dump, kick[:0x40000], base, 256)
    if a: out.append((a, a + 0x40000, 'kick', a - 0xfc0000))  # name by ROM address
    # A hunk executable's header/trailer is not resident slave code. Exclude cached
    # file copies by requiring KickEmu's filled-in resload pointer.
    assert struct.unpack_from('>I',slave,24)[0] == 0x3e9
    payload=slave[32:32+4*struct.unpack_from('>I',slave,28)[0]]
    boot=struct.unpack_from('>H',payload,24)[0]
    assert payload[boot:boot+2] == bytes.fromhex('43fa')
    resload_off=boot+2+struct.unpack_from('>h',payload,boot+2)[0]
    votes=collections.Counter();windows=0
    for off in range(0,len(payload)-16,32):
        word=payload[off:off+16]
        if word.count(0)>8:continue
        windows+=1;i=dump.find(word)
        while i>=0:
            votes[i-off]+=1;i=dump.find(word,i+1)
    matches=[]
    for i,n in votes.most_common():
        if i<0 or i+len(payload)>len(dump) or n<max(4,windows//3):continue
        pointer=struct.unpack_from('>I',dump,i+resload_off)[0]
        if 0<pointer<0x1000000:matches.append(i)
    if len(matches)==1:
        a=base+matches[0];out.append((a,a+len(payload),'slave',a))
    else:raise ValueError(f'live slave missing/ambiguous: {matches}')
    return out


class Namer:
    def __init__(self, regs, mem):
        self.regs, self.mem = regs, mem
        self.libs = {}
        self.starts = set()
        self.extra_labels = {}
        # WHDLoad 20 interrupt forwarding: identified by saved SR, stack checks and
        # the vector lookup. Keep this bounded to the decoded entry/return path.
        sig=bytes.fromhex('514f40d7007c070048e780c0')
        i=-1; entries=[]
        while (i:=mem.dump.find(sig,i+1))>=0:entries.append(mem.base+i)
        for i,start in enumerate(entries):
            end=min(start+0xe0,entries[i+1] if i+1<len(entries) else start+0xe0)
            self.regs.append((start,end,'whd_irq_forward',start))
            self.starts.add(start)
        for lo, hi, name, origin in regs:
            if name == 'slave':
                for off,label in {0x236:'KickEmu_irq_ack',0x280:'KickEmu_wait_blitter',0x2e4:'KickEmu_clear'}.items():
                    self.starts.add(lo+off);self.extra_labels[lo+off]=label
            if name == 'gpc':
                self.starts.update(lo + off for off in (0x6854, 0x7094, 0x729a, 0x772a, 0x776a, 0x782e, 0x8010, 0x818c, 0x8864, 0x906a, 0x9a48, 0xa288, 0xa58c, 0xa6ea, 0xa77c, 0xa8ee, 0xb126, 0xb2f4, 0xc11e, 0xc7f4, 0xce1e, 0xcfd2, 0xd42c, 0xd43e, 0xd4b6))
                for a in range(lo, hi, 2):
                    if mem.word(a) == 0x4e55:  # link a5,#n: Aztec C prologue
                        self.starts.add(a)

    def addr(self, pc):
        if pc is None:
            return '[stopped]'
        if pc == 0x7fffffff:
            return '[CPU overhead]'
        for lo, hi, name, origin in self.regs:
            if lo <= pc < hi:
                return (f'{name}:{pc-origin:05x}' + (f' [{self.extra_labels[pc]}]' if pc in self.extra_labels else '') + (f' [{LABELS[pc-origin]}]' if name=='gpc' and pc-origin in LABELS else '')) if name != 'kick' else f'kick:{pc-origin:06x}' + (f' [{KICK_LABELS[pc-origin]}]' if pc-origin in KICK_LABELS else '')
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
                kinds['stopped' if pc is None else 'CPU-overhead'] += cost
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
    p.add_argument('--base', type=lambda s: int(s, 0), default=0x330000)
    p.add_argument('--top', type=int, default=40)
    p.add_argument('--fields', default=None, help='a-b (0-based, inclusive)')
    a = p.parse_args()
    trace = barto.load(a.trace)
    dump = open(a.dump, 'rb').read()
    mem = Memory(trace, dump, a.base)
    regs = regions(dump, a.base)
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
    print('Attribution: self uses nearest known entry; inclusive follows observed calls. Tail entries and partial calls may differ.')
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
