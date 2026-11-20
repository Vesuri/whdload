#!/usr/bin/env python3
"""Report on a reduced trace from tools/bench.py.

    python3 tools/report.py OUT      rewrite OUT/report.txt from OUT/profile.pkl.gz and
                                     OUT/frames.tsv, and print it

Addresses are runtime addresses; Disk.1 loads at $3b800, so the offset (docs/internals.md)
is address - $3b800. Everything runs in supervisor mode on one stack (the main loop resets
SP to $4b546 each frame), so interrupts nest under the code they interrupt. Interrupt frames
start at the game's handlers (tools/reduction.py); WHDLoad's dispatch before them (its
vector table in fast memory) is billed to the interrupted code and shown by region.
"""
import collections
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reduction import GameReduction  # noqa: E402

DISK = 0x3b800

MARKS = {
    'top': 0x64204,       # the main loop's top: addi.w #1,$c9f4 (a frame begins)
    'render': 0x65174,    # the landscape renderer's entry
    'wait_out': 0x65486,  # the renderer, after waiting for the back buffer's clear
    'swap': 0x58d8c,      # COP1LC write: the frame is shown from the next field
    'clr_req': 0x58d06,   # the next clear requested (after waiting for the previous one)
}
# The renderer's wait for the interrupt-driven clear: tst.w $606ac / bne
SPIN = (0x6547e, 0x65484)
SPINS = {
    'renderer waits for the clear ($6547e)': (0x6547e, 0x65484),
    'clear request waits for the previous clear ($58cfe)': (0x58cfe, 0x58d04),
    'frame limiter $3ca1b ($58e14)': (0x58e14, 0x58e1a),
}

NAMES = {
    0x64204: 'main loop',
    0x672fc: 'main: 672fc', 0x60a1c: 'particles', 0x66718: 'main: 66718',
    0x6249a: 'main: 6249a', 0x65174: 'landscape render', 0x64d74: 'main: objects 64d74',
    0x61f32: 'main: 61f32', 0x58d8c: 'swap', 0x58cfe: 'request clear',
    0x65a78: 'main: 65a78', 0x64356: 'main: 64356',
    0x67d8e: 'polygon fill', 0x673aa: 'objects draw 673aa', 0x64acc: 'render: 64acc',
    0x6584e: 'render: 6584e', 0x60740: 'level 3 (VBL, blitter)', 0x608a8: 'level 2 (keyboard)',
    0x58376: 'VBL: sound', 0x656b2: 'dot plot', 0x6741e: 'object draw 6741e', 0x67932: 'object draw 67932',
}
LOOP_CALLS = [0x672fc, 0x60a1c, 0x66718, 0x6249a, 0x65174, 0x64d74, 0x61f32, 0x58d8c,
              0x58cfe, 0x65a78, 0x64356]


def label(pc):
    if isinstance(pc, tuple):
        return 'IRQ ' + label(pc[1])
    if isinstance(pc, str):
        return pc
    n = NAMES.get(pc, '')
    off = f' (Disk.1 +{pc - DISK:05x})' if DISK <= pc < DISK + 184320 else ''
    return f'${pc:05x}{off} {n}'.rstrip()


OBJECTS = (0x673aa, 0x67400, 0x6735a, 0x67414, 0x67396)


def breakdown(r):
    """The window's cycles in exclusive groups (docs/internals.md's table), summing to all."""
    cat = collections.Counter()
    for st, c in r.stacks.items():
        if any(isinstance(f, tuple) for f in st):
            cat['interrupts'] += c
        elif 0x65174 in st:
            i = st.index(0x65174)
            ch = st[i + 1] if len(st) > i + 1 else None
            if ch is None:
                cat['renderer: own code (grid projection, tile setup)'] += c
            elif ch == 0x67d8e:
                cat['renderer: polygon fill and span writers'] += c
            elif ch in OBJECTS:
                cat['renderer: objects'] += c
            else:
                cat['renderer: helpers'] += c
        elif 0x60a1c in st:
            cat['particles'] += c
        elif 0x62236 in st:
            cat['fade-in'] += c
        else:
            cat['rest of the main loop'] += c
    wait = r.self[0x6547e] + r.self[0x65484]
    fade = r.self[0x58e14] + r.self[0x58e1a]
    cat['renderer: own code (grid projection, tile setup)'] -= wait
    cat['fade-in'] -= fade
    cat['waiting for the blitter clear'] = wait
    cat['fade-in wait'] = fade
    return cat


def report(r, rows=None):
    lines = []
    w = lines.append
    nf = len(r.fields)
    cpf = statistics.mean(f['cycles'] for f in r.fields)   # profiler cycle units per field
    tot = r.total()
    ms = lambda c: 20.0 * c / cpf                            # noqa: E731  PAL field = 20 ms
    w(f'Window: {nf} fields ({nf / 50:.1f} s PAL), {cpf:.0f} cycle units a field; '
      f'traced {100 * tot / (cpf * nf):.2f}% of them (exception gaps '
      f'{100 * sum(f["gap"] for f in r.fields) / tot:.2f}%, STOP {100 * sum(f["nopc"] for f in r.fields) / tot:.2f}%)')

    # frames
    tops = [p for n, p, _ in r.events if n == 'top']
    if rows:
        frames = rows[-1][1] - rows[0][1]
        w(f'Frames (the game counter $c9f4): {frames} in {nf} fields = {50 * frames / nf:.2f} fps, '
          f'{nf / frames:.2f} fields a frame')
        rates = [50 * (b1 - b0) / (a1 - a0) for (a0, b0), (a1, b1) in zip(rows, rows[1:])]
        w(f'  per {rows[1][0] - rows[0][0]}-field chunk: fps min {min(rates):.1f}, '
          f'median {statistics.median(rates):.1f}, max {max(rates):.1f}')
        w('  ' + ' '.join(f'{x:.0f}' for x in rates))
    if len(tops) > 2:
        d = [ms(b - a) for a, b in zip(tops, tops[1:])]
        q = statistics.quantiles(d, n=100)
        w(f'Frame time (main loop top to top, {len(d)} frames): mean {statistics.mean(d):.1f} ms, '
          f'p50 {q[49]:.1f}, p95 {q[94]:.1f}, max {max(d):.1f}, min {min(d):.1f}')
        hist = collections.Counter(min(round(x / 20), 6) for x in d)
        w('  fields a frame (rounded): ' + ', '.join(f'{k}{"+" if k == 6 else ""}: {v}'
                                                   for k, v in sorted(hist.items())))
        # per frame: the clear wait
        wait = {}
        ev = [(n, p, t) for n, p, t in r.events if n in ('top', 'render', 'wait_out')]
        waits, works = [], []
        i_top = [i for i, e in enumerate(ev) if e[0] == 'top']
        for a, b in zip(i_top, i_top[1:]):
            seg = ev[a:b + 1]
            sp = seg[-1][2] - seg[0][2]
            waits.append(ms(sp))
            works.append(ms(seg[-1][1] - seg[0][1]) - ms(sp))
        w(f'  of which the renderer waits for the clear: mean {statistics.mean(waits):.1f} ms, '
          f'p50 {statistics.median(waits):.1f}; everything else: mean {statistics.mean(works):.1f} ms, '
          f'p50 {statistics.median(works):.1f}, max {max(works):.1f}')
    w('')

    # exclusive split: interrupts, spins, main-loop children
    irq = collections.Counter()
    top = collections.Counter()
    spin_pcs = {pc for v in SPINS.values() for pc in v}
    for st, c in r.stacks.items():
        h = next((fr for fr in st if isinstance(fr, tuple)), None)
        if h is not None:
            irq[h[1]] += c
            continue
        fr = next((fr for fr in st if fr in LOOP_CALLS), None)
        top[fr if fr is not None else (st[0] if st else 'main loop itself')] += c
    spin = {k: sum(r.self[pc] for pc in v) for k, v in SPINS.items()}
    w('Where the time goes (exclusive groups, summing to all traced cycles)')
    for k, c in breakdown(r).most_common():
        w(f'  {k:58} {ms(c / nf):6.2f} ms  {100 * c / tot:6.2f}%')
    w('')
    w('In detail (ms per field and share of all traced time)')
    w(f'  {"interrupts (all)":58} {ms(sum(irq.values()) / nf):6.2f} ms  {100 * sum(irq.values()) / tot:6.2f}%')
    for h, c in irq.most_common(6):
        w(f'    {label(h):56} {ms(c / nf):6.2f} ms  {100 * c / tot:6.2f}%')
    w(f'  {"busy-waits (outside interrupts)":58} {ms(sum(spin.values()) / nf):6.2f} ms  {100 * sum(spin.values()) / tot:6.2f}%')
    for k, c in spin.items():
        w(f'    {k:56} {ms(c / nf):6.2f} ms  {100 * c / tot:6.2f}%')
    w('  main-loop calls, without interrupts (busy-waits included where they sit):')
    for fr, c in top.most_common(14):
        w(f'    {label(fr):56} {ms(c / nf):6.2f} ms  {100 * c / tot:6.2f}%')
    if hasattr(r, 'irqs') and r.irqs:
        w('  interrupt entries: ' + ', '.join(f'{label(h)} {n} ({n / nf:.2f} a field)'
                                              for h, n in r.irqs.most_common()))
    l3 = [(st, c) for st, c in r.stacks.items() if ('irq', 0x60740) in st]
    if l3:
        snd = sum(c for st, c in l3 if 0x58376 in st)
        blt = sum(c for pc, c in r.self.items() if 0x60844 <= pc < 0x608a8)
        allc = sum(c for _, c in l3)
        w(f'  level 3: sound (VBL $58376) {ms(snd / nf):.2f} ms, blitter-done chaining '
          f'{ms(blt / nf):.2f} ms, rest of the VBL {ms((allc - snd - blt) / nf):.2f} ms a field')
    reg = collections.Counter()
    for pc, c in r.self.items():
        reg['game (chip)' if pc < 0x80000 else 'Kickstart ROM' if pc >= 0xf80000
            else 'WHDLoad and slave (fast)'] += c
    w('  self time by region: ' + ', '.join(f'{k} {100 * v / tot:.2f}%' for k, v in reg.most_common()))
    w('')
    w('Call tree (inclusive, children of 1% and more)')
    w(r.tree(label=label, min_share=0.01, depth=6))
    w('')
    w('Hottest instructions (self, busy-waits excluded)')
    for pc, c in [x for x in r.self.most_common(60) if x[0] not in spin_pcs][:25]:
        w(f'  {label(pc):44} {100 * c / tot:6.2f}%  {r.counts[pc]:9d} executions')
    w('')
    funcs = collections.Counter()
    for st, c in r.stacks.items():
        if st:
            funcs[st[-1]] += c
    w('Self time by innermost routine')
    for fr, c in funcs.most_common(15):
        w(f'  {label(fr):56} {100 * c / tot:6.2f}%')
    w('')
    w('Chip bus slots: ' + ', '.join(f'{k} {100 * v:.1f}%' for k, v in r.dma_shares().items()))
    return '\n'.join(lines) + '\n'


def main(args):
    if not args:
        sys.exit(__doc__)
    out = Path(args[0])
    r = GameReduction.load(out / 'profile.pkl.gz')
    rows = None
    if (out / 'frames.tsv').exists():
        rows = [tuple(int(x) for x in l.split('\t')) for l in (out / 'frames.tsv').read_text().splitlines()[1:]]
    text = report(r, rows)
    (out / 'report.txt').write_text(text)
    print(text)


if __name__ == '__main__':
    main(sys.argv[1:])
