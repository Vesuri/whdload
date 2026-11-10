#!/usr/bin/env python3
"""The level-1 benchmark: boot, drive the route, trace the 10-second window, report.

    tools/bench.py OUT [route steps...]     (SETUP, EXTRA_ARGS, SLAVE, INSTANCE pass through)

Boots with tools/boot.sh (stopped at the game's entry, warp, deterministic, nothing in
port 0), plays tools/route.py's `start` and `aim` (fire is then held), and traces the window:
WINDOW fields (default 500, 10 s PAL) in 100-field chunks back to back, each reduced with
amigaxdev.callprofile and tools/chipprofile.py and deleted. On a1200-030 without its MMU the enemy explodes at fields
140-200 of the window (score 15, targets 16 at the end). Writes OUT/profile.pkl.gz,
OUT/chip.pkl.gz and OUT/chip.txt (chip accesses by routine, data flow, DMA pages), OUT/end.png (the field after the window) and OUT/report.txt.

The trace needs a cycle-exact CPU without an MMU: on a1200-030 pass
EXTRA_ARGS=--uae_mmu_model=0 (WHDLoad does not use the 68030's MMU without its MMU option).
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
import route  # noqa: E402
from amigaxdev import barto  # noqa: E402
from amigaxdev.callprofile import Reduction  # noqa: E402
from chipprofile import ChipReduction, report as chip_report  # noqa: E402

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


def main(argv):
    out = ROOT / argv[0]
    steps = argv[1:] or ['start', 'aim']
    window = int(os.environ.get('WINDOW', 500))
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(ROOT / 'tools/boot.sh')], check=True)
    try:
        route.run(steps)
        red = Reduction(marks={'swap': SWAP, 'vbl': VBL, 'go': GO}, tally=WAIT)
        chip = ChipReduction()
        for i in range(0, window, 100):
            chunk = out / 'chunk.bin'
            route.run([f'prof {min(100, window - i)} {chunk.relative_to(ROOT)}'])
            t = barto.load(str(chunk))
            red.feed(t)
            chip.feed(t)
            del t
            chunk.unlink()
        route.req('shot', str(out / 'end.png'))
        route.run(['-JOY2_FIRE_BUTTON'])
    finally:
        subprocess.run([sys.executable, str(ROOT / 'tools/encounter.py'), 'quit'],
                       capture_output=True)
    red.save(str(out / 'profile.pkl.gz'))
    chip.save(str(out / 'chip.pkl.gz'))
    (out / 'chip.txt').write_text(chip_report(chip))
    rep = report(red, window)
    (out / 'report.txt').write_text(rep)
    print(rep)


def report(red, window):
    swaps = [e for e in red.events if e[0] == 'swap']
    vbls = [e for e in red.events if e[0] == 'vbl']
    total = red.total()
    lines = [f'fields {len(red.fields)}  vbl entries {len(vbls)}  frames (swaps) {len(swaps)}  '
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
    # Work per frame (between pacing-wait exits, the wait excluded, interrupts included), in fields.
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
    lines.append('DMA slots: ' + ', '.join(f'{k} {v:.1%}' for k, v in red.dma_shares().items()))
    lines.append('')
    lines.append('self cycles by PC (top 40), % of traced cycles:')
    for pc, c in red.self.most_common(40):
        lines.append(f'  {pc:06x}  {c:10d}  {100 * c / total:5.1f}%  x{red.counts[pc]}')
    lines.append('')
    lines.append('main-loop routines, inclusive (interrupts that hit them included), % of traced cycles:')
    inc = red.inclusive()
    for pc, what in MAIN:
        lines.append(f'  {pc:06x}  x{red.counts[pc]:6d}  {100 * inc[pc] / total:5.1f}%  {what}')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main(sys.argv[1:])
