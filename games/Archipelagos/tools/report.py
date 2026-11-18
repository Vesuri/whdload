#!/usr/bin/env python3
"""Report on a reduced trace from tools/bench.py.

    python3 tools/report.py OUT      rewrite OUT/report.txt from OUT/profile.pkl.gz and
                                     OUT/state.tsv, and print it

Addresses are runtime addresses of the program (loaded to $2000, its body at $201c:
offset = address - $201c, docs/internals.md uses offsets). Everything runs in supervisor
mode on one stack ($784-$800), so a single call stack nests the interrupts correctly
(tools/reduction.py).
"""
import collections
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reduction import GameReduction  # noqa: E402

BODY = 0x201c

MARKS = {
    'loop': 0x13806,     # the in-game loop's top
    'tick': 0x1171c,     # a world tick runs (its countdown $149d2 went below 0)
    'render': 0x13ae2,   # the renderer's entry
    'swap': 0x1422c,     # the buffers are exchanged: a frame is shown from the next field
    'vw_in': 0x143d0,    # wait for the next field (the VBL counter $1487e to change)
    'vw_out': 0x143e2,   # ... it changed
    'ret_rw': 0x13b06,   # return from the renderer's own wait, before it draws
    'ret_lw': 0x1387e,   # return from the in-game loop's wait, before the swap
    'bw_in': 0x13f16,    # wait for the blitter (BLTBUSY), called before each blit
    'bw_out': 0x13f24,   # ... done
}
VBL_SPIN = (0x143da, 0x143e0)          # the VBL wait's loop: cmp.l $1487e,d0 / bne
BLIT_SPIN = (0x13f18, 0x13f1e, 0x13f22)  # the blitter wait's loop

NAMES = {
    0x13806: 'game loop', 0x11712: 'world update', 0x13ae2: 'render',
    0x143d0: 'wait VBL', 0x1422c: 'swap', 0x14322: 'show buffer', 0x13f16: 'wait blitter',
    0x13b8e: 'draw view', 0xee36: 'level 3 handler', 0x2030: 'replayer tick',
    0x21dc: 'replayer', 0xff16: 'pointer (VBL)', 0x1011e: 'pan (VBL)', 0x102b2: 'buttons (VBL)',
}
REGIONS = [
    ((0x2000, 0x16314), 'game program'),
    ((0x16314, 0x80000), 'game data / buffers'),
    ((0xf80000, 0x1000000), 'Kickstart ROM'),
    ((0x200000, 0x10000000), 'fast memory (WHDLoad, slave)'),
]


def label(pc):
    if isinstance(pc, str):
        return pc
    n = NAMES.get(pc, '')
    off = f'+{pc - BODY:05x}' if BODY <= pc < 0x16314 else ''
    return f'{pc:06x}{off} {n}'.rstrip()


def region(pc):
    for (a, b), n in REGIONS:
        if a <= pc < b:
            return n
    return 'other'


def pct(x, tot):
    return f'{100 * x / tot:6.2f}%'


def report(r, states=None, meta=None, hz=50):
    meta = meta or {}
    lines = []
    w = lines.append
    tot = r.total()
    nf = len(r.fields)
    cpf = statistics.mean(f['cycles'] for f in r.fields)
    ms = 1000 / hz
    bounds = [0]
    for f in r.fields:
        bounds.append(bounds[-1] + f['total'])

    def field_at(pos):
        lo, hi = 0, len(bounds) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if bounds[mid] <= pos:
                lo = mid
            else:
                hi = mid
        return lo + (pos - bounds[lo]) / max(1, bounds[lo + 1] - bounds[lo])

    ev = r.events
    swaps = [p for n, p, _ in ev if n == 'swap']
    w(f'traced {nf} fields ({nf / hz:.2f} s), {tot} cycles, {cpf:.0f} a field'
      + (f'; pan {meta["pan"]} fields at {meta["dx"]} counts a field' if meta else ''))
    if len(swaps) > 1:
        gaps = [field_at(b) - field_at(a) for a, b in zip(swaps, swaps[1:])]
        span = field_at(swaps[-1]) - field_at(swaps[0])
        fps = (len(swaps) - 1) / span * hz
        w(f'frames shown {len(swaps)}: {fps:.2f} fps between the first and last swap; '
          f'fields a frame mean {statistics.mean(gaps):.2f}, min {min(gaps):.2f}, max {max(gaps):.2f}')
        hist = collections.Counter(round(g) for g in gaps)
        w('fields a frame (rounded): ' + ', '.join(f'{k}: {v}' for k, v in sorted(hist.items())))
    ticks = [p for n, p, _ in ev if n == 'tick']
    w(f'world ticks {len(ticks)} in {nf} fields: one every {nf / max(1, len(ticks)):.2f} fields')

    # Waits: VBL spin per call site, blitter spans.
    site = collections.Counter()
    pending = None
    for n, p, t in ev:
        if n == 'vw_in':
            pending = (p, t)
        elif n == 'vw_out' and pending:
            spin = t - pending[1]
            pending = ('done', spin)
        elif n in ('ret_rw', 'ret_lw') and pending and pending[0] == 'done':
            site[n] += pending[1]
            pending = None
    blit, bin_ = 0, None
    nblit = 0
    for n, p, t in ev:
        if n == 'bw_in':
            bin_ = p
        elif n == 'bw_out' and bin_ is not None:
            blit += p - bin_
            nblit += 1
            bin_ = None
    blit_spin = sum(r.self[pc] for pc in BLIT_SPIN)
    vbl_spin = sum(r.self[pc] for pc in VBL_SPIN)
    incl = r.inclusive()
    irq = sum(c for st, c in r.stacks.items() if any(isinstance(fr, tuple) for fr in st))
    nirq = getattr(r, 'irqs', {})
    frames = max(1, len(swaps) - 1) if len(swaps) > 1 else 1
    per = lambda c: f'{c / frames / cpf * ms:6.2f} ms a frame'  # noqa: E731
    w('')
    w('Where the time goes (share of all traced cycles; ms a frame over the frames shown):')
    w(f'  wait VBL, renderer before drawing    {pct(site["ret_rw"], tot)}  {per(site["ret_rw"])}')
    w(f'  wait VBL, game loop before the swap  {pct(site["ret_lw"], tot)}  {per(site["ret_lw"])}')
    w(f'  wait VBL, all spin                   {pct(vbl_spin, tot)}  {per(vbl_spin)}')
    w(f'  wait blitter ({nblit} calls)           {pct(blit, tot)}  {per(blit)}  (spin {pct(blit_spin, tot)})')
    w(f'  interrupts (inclusive)               {pct(irq, tot)}  {per(irq)}  entries '
      + ', '.join(f'{label(k)} {v}' for k, v in sorted(nirq.items())))
    for pc in (0x2030, 0xff16, 0x1011e, 0x102b2):
        if incl[pc]:
            w(f'    {label(pc):34} {pct(incl[pc], tot)}  {per(incl[pc])}')
    for pc in (0x13ae2, 0x13b8e, 0x11712, 0x1422c):
        w(f'  {label(pc):36} {pct(incl[pc], tot)}  {per(incl[pc])} (inclusive)')
    w(f'  trace gap records (CPU overhead)     {pct(getattr(r, "gaps", 0), tot)}')
    work = tot - vbl_spin - blit_spin
    w(f'  CPU work (all but the two spins)     {pct(work, tot)}  {per(work)}')
    reg = collections.Counter()
    for pc, c in r.self.items():
        reg[region(pc)] += c
    w('By where the code runs:')
    for k, c in reg.most_common():
        w(f'  {k:36} {pct(c, tot)}')

    if len(swaps) > 1:
        tal = {p: t for n, p, t in ev}
        bl = []
        binp = None
        bl_by_pos = []
        for n, p, t in ev:
            if n == 'bw_in':
                binp = p
            elif n == 'bw_out' and binp is not None:
                bl_by_pos.append((binp, p))
                binp = None
        fw = []
        j = 0
        for a, b in zip(swaps, swaps[1:]):
            spin = tal[b] - tal[a]
            bs = 0
            while j < len(bl_by_pos) and bl_by_pos[j][0] < b:
                s, e = bl_by_pos[j]
                if s >= a:
                    bs += e - s
                j += 1
            fw.append((b - a - spin - bs) / cpf)
        fw.sort()
        q = lambda x: fw[min(len(fw) - 1, int(x * len(fw)))]  # noqa: E731
        w('')
        w(f'Work a frame without the VBL and blitter waits, in fields: mean {statistics.mean(fw):.2f}, '
          f'p50 {q(.5):.2f}, p95 {q(.95):.2f}, max {fw[-1]:.2f}')

    w('')
    w('DMA slots: ' + ', '.join(f'{k} {v * 100:.1f}%' for k, v in r.dma_shares().items()))

    if states:
        hd = [s[1] for s in states]
        turned = sum((b - a) % 720 for a, b in zip(hd, hd[1:]))
        w(f'heading: {hd[0]} -> {hd[-1]}, turned {turned / 2:.0f} degrees in {len(hd) - 1} fields')

    w('')
    w('Call tree (inclusive, >= 0.5%):')
    w(r.tree(label=label, min_share=0.005, depth=7))

    selfn = collections.Counter()
    for st, c in r.stacks.items():
        fn = next((fr for fr in reversed(st) if not isinstance(fr, str)), 'top')
        if isinstance(fn, tuple):
            fn = fn[1]
        selfn[fn] += c
    w('')
    w('Self time by routine (innermost call frame):')
    for fn, c in selfn.most_common(25):
        w(f'  {label(fn):40} {pct(c, tot)}')
    w('')
    w('Hottest instructions:')
    for pc, c in r.self.most_common(30):
        w(f'  {label(pc):40} {pct(c, tot)}  x{r.counts[pc]}')
    return '\n'.join(lines) + '\n'


def main(args):
    out = Path(args[0])
    r = GameReduction.load(out / 'profile.pkl.gz')
    states = None
    st = out / 'state.tsv'
    if st.exists():
        rows = st.read_text().splitlines()[1:]
        states = [[int(v) for v in row.split('\t')] for row in rows]
    text = report(r, states)
    (out / 'report.txt').write_text(text)
    print(text)


if __name__ == '__main__':
    main(sys.argv[1:])
