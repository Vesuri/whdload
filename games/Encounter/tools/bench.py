#!/usr/bin/env python3
"""The level-1 benchmark: boot, drive the route, trace the 10-second window, report.

    tools/bench.py OUT [route steps...]     (SETUP, EXTRA_ARGS, SLAVE, INSTANCE pass through)

With the Enhanced main loop (50 Hz presentation) its own marks are used (route.eloop()):
a frame is a presented frame, and the logic frames (world steps) are counted apart.

Boots with tools/boot.sh (stopped at the game's entry, warp, deterministic, nothing in
port 0), plays tools/route.py's `start` and `aim` (fire is then held), and traces the window:
WINDOW fields (default 500, 10 s PAL) in 100-field chunks back to back, each reduced with
amigaxdev.callprofile and tools/chipprofile.py and deleted. On a1200-030 without its MMU the enemy explodes at fields
140-200 of the window (score 15, targets 16 at the end). Writes OUT/profile.pkl.gz,
OUT/chip.pkl.gz and OUT/chip.txt (chip accesses by routine, data flow, DMA pages),
OUT/flow.pkl.gz (tools/dataflow.py: every CPU data access below $13000 by address),
OUT/end.png (the field after the window) and OUT/report.txt.

With Enhanced framerate the game runs from its copy in the ExpMem (tools/route.py
copy_delta()): the marks are set on the copy, instructions are decoded from their chip
originals, and the report and the reductions name routines by their chip addresses.

The trace needs a cycle-exact CPU without an MMU: on a1200-030 pass
EXTRA_ARGS=--uae_mmu_model=0 (WHDLoad does not use the 68030's MMU without its MMU option).
"""
import collections
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
import route  # noqa: E402
from amigaxdev import barto, callprofile  # noqa: E402
from amigaxdev.callprofile import Reduction  # noqa: E402
import chipprofile  # noqa: E402
from chipprofile import ChipReduction, report as chip_report  # noqa: E402
from dataflow import DataFlow  # noqa: E402

# Game addresses (base memory, absolute; see docs/internals.md "Frames and time").
SWAP = 0xDEA4        # end of frame: the new front buffer is published (both branches join here)
VBL = 0x804E         # level-3 handler: addq.l #1,$11DEA, then the per-field work
GO = 0xDED2          # pacing wait done: move.w d1,$11ECC (the next frame's work starts)
WAIT = (0xE28C, 0xE292, 0xE298, 0xE29A)   # wait-for-next-field loop (the frame pacing wait)

# The main loop ($DA30) in call order; inclusive cycles are reported per entry.
MAIN = [(0xDF94, 'frame setup'), (0xD636, ''), (0xD374, ''), (0x10B48, ''), (0xCD14, ''),
        (0xDDC0, 'object draw loop'), (0x9D10, ''), (0xD362, ''),
        (0xDE3E, 'frame end: swap + pacing wait'), (0xE28C, '  of which the wait'),
        (0xED76, ''), (0xA1F6, ''),
        (0xA836, 'per-field step (x elapsed fields, max 3)'), (0xE7AA, 'per-field: input, heading, player'),
        (0xFD26, 'per-field'), (0xA570, 'per-frame sim'), (0xE29E, 'per-frame: object motion'),
        (0xF0A6, 'per-frame'), (0xCC2C, 'per-frame'), (0xF2CA, 'per-frame'),
        (0xEE86, 'per-frame: collision tests'), (0xE32A, 'per-frame'), (0xE724, 'per-frame: depth sort'),
        (0xBB22, 'called inside the draw (polygon?)'), (0xDFE6, ''), (0xBFB8, ''), (0xFA58, '')]

# Phase marks (Enhanced main loop): the entries it calls in order. The time from one mark to
# the next is the phase's, so the slave's own work between calls is in the phase before it
# (the staged frame's save and _objstage in the logic head's, its restore in $D362's).
PHASES = [(0xED76, 'world'), (0xE32A, 'transform'), (0xE724, 'sort'), (0xC536, 'keys'),
          (0xDF94, 'clear'), (0xD636, 'd636'), (0xD374, 'd374'), (0x10B48, '10b48'),
          (0xCD14, 'horizon'), (0xDDC0, 'objects'), (0x9D10, 'radar'), (0xD362, 'd362')]


def main(argv):
    out = ROOT / argv[0]
    steps = argv[1:] or ['start', 'aim']
    window = int(os.environ.get('WINDOW', 500))
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(ROOT / 'tools/boot.sh')], check=True)
    try:
        route.run(steps)
        delta = route.copy_delta()
        to_copy = lambda pc: pc + delta if route.COPY[0] <= pc < route.COPY[1] else pc  # noqa: E731
        to_chip = lambda pc: pc - delta if route.COPY[0] + delta <= pc < route.COPY[1] + delta else pc  # noqa: E731
        if delta:
            for mod in (callprofile, chipprofile):
                native = mod._opkind
                mod._opkind = lambda t, pc, cache, native=native: native(t, to_chip(pc), cache)
        el = route.eloop()
        wait = tuple(map(to_copy, WAIT))
        if el:   # the Enhanced main loop: its swap, field-wait exit and logic head, the phases;
            # the clear-ahead's wait for the beam is waiting too
            marks = {'swap': el['swap'], 'vbl': to_copy(VBL), 'go': el['go'], 'logic': el['hash'],
                     'preclear': el['preclr'], 'staged': el['stage']}
            marks.update({name: to_copy(pc) for pc, name in PHASES})
            marks['clear'] = el['clear']   # the loop's own clear, not $DF94
            wait += tuple(range(el['prew'][0], el['prew'][1], 2))
        else:
            marks = {'swap': to_copy(SWAP), 'vbl': to_copy(VBL), 'go': to_copy(GO), 'logic': to_copy(route.LOOP)}
        red = Reduction(marks=marks, tally=wait)
        chip = ChipReduction(map_pc=to_chip)
        flow = DataFlow(map_pc=to_chip)
        for i in range(0, window, 100):
            chunk = out / 'chunk.bin'
            route.run([f'prof {min(100, window - i)} {chunk.relative_to(ROOT)}'])
            t = barto.load(str(chunk))
            red.feed(t)
            chip.feed(t)
            flow.feed(t)
            del t
            chunk.unlink()
        route.req('shot', str(out / 'end.png'))
        route.run(['-JOY2_FIRE_BUTTON'])
    finally:
        subprocess.run([sys.executable, str(ROOT / 'tools/encounter.py'), 'quit'],
                       capture_output=True)
    red.save(str(out / 'profile.pkl.gz'))
    chip.save(str(out / 'chip.pkl.gz'))
    flow.save(str(out / 'flow.pkl.gz'))
    (out / 'chip.txt').write_text(chip_report(chip))
    rep = report(red, window, to_copy, to_chip, delta) + code_fetches(chip)
    (out / 'report.txt').write_text(rep)
    print(rep)


def code_fetches(chip):
    """The CPU's code fetches from chip memory, per field, and where they come from (16-byte
    granules merged into ranges). With the code copied to the ExpMem this should be empty."""
    n = sum(c for (i, k), c in chip.acc.items() if k == 'code')
    gran = collections.Counter()
    for top, c in chip.ccount.items():
        gran.update(c)
    rs = chipprofile.ranges(gran, 4)
    out = [f'chip code fetches per field: {n / max(1, chip.fields):.0f}']
    if rs:
        out.append('  from ' + chipprofile.fmt_ranges(rs, 24))
    return '\n'.join(out) + '\n'


def phases(red, fc):
    """Per presented frame (go to go), lines (of 313 a field) from each mark to the next, the
    wait excluded, by frame kind: the world step with a staged frame, the world step with
    the committed frame (no staged frame), or the committed frame (its transform, the
    logic head, the draw)."""
    names = {name for _, name in PHASES} | {'logic', 'swap', 'preclear', 'staged'}
    ev = [e for e in red.events if e[0] in names or e[0] == 'go']
    kinds = collections.defaultdict(lambda: [0, collections.Counter(), []])
    cur, tot = collections.Counter(), 0
    seen = []
    for a, b in zip(ev, ev[1:]):
        if a[0] == 'go':
            if seen:
                k = ('world + staged' if 'staged' in seen else
                     'world + committed' if 'world' in seen else 'committed')
                kinds[k][0] += 1
                kinds[k][1].update(cur)
                kinds[k][2].append(tot)
            cur, tot, seen = collections.Counter(), 0, []
        name = 'preclear' if a[0] == 'clear' and seen and seen[-1] == 'preclear' else a[0]
        seen.append(name)
        c = ((b[1] - a[1]) - (b[2] - a[2])) * 313 / fc
        cur[name] += c
        tot += c
    out = ['phases per presented frame, lines (313 a field), from each mark to the next, wait excluded:']
    for k, (n, c, ts) in sorted(kinds.items()):
        ts.sort()
        out.append(f'  {k}: n={n}  total median {ts[len(ts) // 2]:.0f}  p90 {ts[int(len(ts) * .9)]:.0f}  '
                   f'max {ts[-1]:.0f}')
        out.append('    ' + '  '.join(f'{name} {v / n:.1f}' for name, v in
                                       sorted(c.items(), key=lambda x: -x[1]) if v / n >= 0.5))
    return out


def report(red, window, to_copy=lambda pc: pc, to_chip=lambda pc: pc, delta=0):
    swaps = [e for e in red.events if e[0] == 'swap']
    vbls = [e for e in red.events if e[0] == 'vbl']
    total = red.total()
    lines = [f'code copy at chip + ${delta:x}' if delta else 'code in chip',
             f'fields {len(red.fields)}  vbl entries {len(vbls)}  frames (swaps) {len(swaps)}  '
             f'fps {50 * len(swaps) / len(red.fields):.2f}  fields/frame {len(red.fields) / max(1, len(swaps)):.3f}',
             f'traced cycles {total}  pacing wait {red.tallied} ({100 * red.tallied / total:.1f}%)']
    # Fields per frame histogram from swap positions converted to fields.
    bounds, acc = [], 0
    for f in red.fields:
        acc += f['total']
        bounds.append(acc)
    import bisect
    fidx = [bisect.bisect_right(bounds, e[1]) for e in swaps]
    from collections import Counter
    hist = Counter(b - a for a, b in zip(fidx, fidx[1:]))
    lines.append('fields between swaps: ' + ', '.join(f'{k}:{v}' for k, v in sorted(hist.items())))
    # World steps: the Enhanced loop's world mark, else the logic head
    wname = 'world' if any(e[0] == 'world' for e in red.events) else 'logic'
    logic = [e for e in red.events if e[0] == wname]
    lidx = [bisect.bisect_right(bounds, e[1]) for e in logic]
    lhist = Counter(b - a for a, b in zip(lidx, lidx[1:]))
    lines.append(f'logic frames (world steps) {len(logic)}  per second {50 * len(logic) / len(red.fields):.2f}  '
                 'fields between: ' + ', '.join(f'{k}:{v}' for k, v in sorted(lhist.items())))
    # Work per frame (between pacing-wait exits, the wait excluded, interrupts included), in
    # fields. With the Enhanced loop a frame is a presented frame: a logic frame's work is
    # counted in the frame it starts.
    fc = total / len(red.fields)
    gos = [e for e in red.events if e[0] == 'go']
    seq = [(bisect.bisect_right(bounds, a[1]), ((b[1] - a[1]) - (b[2] - a[2])) / fc)
           for a, b in zip(gos, gos[1:])]
    work = sorted(w for _, w in seq)
    if work:
        n = len(work)
        lines.append(f'work per frame in fields (n={n}): min {work[0]:.3f}  median {work[n // 2]:.3f}  '
                     f'p90 {work[int(n * .9)]:.3f}  max {work[-1]:.3f}  mean {sum(work) / n:.3f}  '
                     f'frames over 1 field {sum(w > 1 for w in work)}')
    lines.append('work per frame by window position (fields: mean / max):')
    for lo in range(0, len(red.fields), 50):
        ws = [w for f, w in seq if lo <= f < lo + 50]
        if ws:
            lines.append(f'  {lo:4d}-{lo + 49:4d}  {sum(ws) / len(ws):.3f} / {max(ws):.3f}  ' + '#' * round(20 * max(ws)))
    if any(e[0] == 'clear' for e in red.events):
        lines += phases(red, fc)
    lines.append('DMA slots: ' + ', '.join(f'{k} {v:.1%}' for k, v in red.dma_shares().items()))
    lines.append('')
    lines.append('self cycles by PC (top 40; * runs from the copy), % of traced cycles:')
    for pc, c in red.self.most_common(40):
        lines.append(f'  {to_chip(pc):06x}{"*" if pc != to_chip(pc) else " "} {c:10d}  {100 * c / total:5.1f}%  x{red.counts[pc]}')
    lines.append('')
    lines.append('main-loop routines, inclusive (interrupts that hit them included), % of traced cycles:')
    inc = red.inclusive()
    for pc, what in MAIN:
        lines.append(f'  {pc:06x}  x{red.counts[to_copy(pc)]:6d}  {100 * inc[to_copy(pc)] / total:5.1f}%  {what}')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main(sys.argv[1:])
