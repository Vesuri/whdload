#!/usr/bin/env python3
"""The race benchmark: boot, drive the route, trace a window of the first race, report.

    tools/bench.py OUT [route steps...]     (SETUP, EXTRA_ARGS, SLAVE, WHD_ARGS, INSTANCE pass through)

Boots with tools/boot.sh (stopped at the game's entry, warp, deterministic, nothing in
port 0), plays tools/route.py's `race` (Offroad, joystick up held from the start), and traces
WINDOW fields (default 500, 10 s PAL) in 100-field chunks back to back, each reduced with
amigaxdev.callprofile and tools/chipprofile.py and deleted. Writes OUT/profile.pkl.gz,
OUT/chip.pkl.gz, OUT/chip.txt, OUT/end.png (the field after the window) and OUT/report.txt.

The trace needs a cycle-exact CPU without an MMU: on a1200-030 pass
EXTRA_ARGS=--uae_mmu_model=0 (WHDLoad does not use the 68030's MMU without its MMU option).
"""
import bisect
import collections
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
import route  # noqa: E402
from amigaxdev import barto  # noqa: E402
from amigaxdev.callprofile import Reduction  # noqa: E402
import chipprofile  # noqa: E402
from amigaxdev import callprofile  # noqa: E402
from chipprofile import ChipReduction, report as chip_report  # noqa: E402

# Game addresses as program offsets (runtime = program base + offset; the base is $400 in the
# shipped slave, docs/internals.md); route.prog_base() finds the base of the running build.
SWAP = 0x2688        # after the slave's _LockFrameRate: COP1LC written, the frame is published
GO = 0x2694          # the swap's wait for the next field returned: the next frame's work starts
VBL = 0x4DAC         # level-3 handler (VERTB only): addq.w #1,$6AD8, sound sequencer
WAIT = (0x4B84, 0x4B8A)          # the game's wait for the next field after the swap
# The slave's _LockFrameRate wait loop (.DelayLoop, 3 instructions); the slave base comes from
# $BC (trap #15 -> _SaveHighScores), offsets from the build's listing (BUILD, default release).

MAIN = [(0x153E, 'race loop 1'), (0x6716, 'race loop 2'), (0x1E2, 'race loop 3 (blitter clear first)'),
        (0x33BE, 'race loop 4'), (0x448A, 'race loop 5'), (0x2672, 'swap + lock + field wait'),
        (0x4B7C, '  field wait')]


def listing_symbols():
    lst = ROOT / f'tmp/build/{os.environ.get("BUILD", "release")}/BuggyBoy.lst'
    sym = {}
    for line in lst.read_text(encoding='latin-1').splitlines():
        m = re.match(r'^([0-9A-F]{8}) (_\w+)$', line)
        if m:
            sym[m.group(2)] = int(m.group(1), 16)
        m = re.match(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+: \.DelayLoop', line)
        if m:
            sym['.DelayLoop'] = int(m.group(1), 16)
    return sym


def see_program(image, prog):
    """Let both reductions tell JSR/BSR apart in a program outside chip memory: the traces
    snapshot only chip, slow and ROM, so code in fast memory is read from IMAGE (bytes from
    PROG on)."""
    def wrap(orig):
        def opkind(t, pc, cache):
            o = pc - prog
            if 0 <= o < len(image) - 1 and pc >= len(t.chip):
                k = cache.get(pc)
                if k is None:
                    w = int.from_bytes(image[o:o + 2], 'big')
                    k = cache[pc] = 1 if (w & 0xffc0) == 0x4e80 or (w & 0xff00) == 0x6100 else 0
                return k
            return orig(t, pc, cache)
        return opkind
    callprofile._opkind = wrap(callprofile._opkind)
    chipprofile._opkind = wrap(chipprofile._opkind)


def slave_base(sym):
    return route.peek(0xBC) - sym['_SaveHighScores']


def main(argv):
    out = ROOT / argv[0]
    steps = argv[1:] or ['race']
    window = int(os.environ.get('WINDOW', 500))
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(ROOT / 'tools/boot.sh')], check=True)
    try:
        route.run(steps)
        sym = listing_symbols()
        base = slave_base(sym)
        prog = route.prog_base()
        lock = tuple(base + sym['.DelayLoop'] + o for o in (0, 2, 4))
        img = out / 'program.bin'
        route.req('gdb', f'dump binary memory {img.relative_to(ROOT)} {prog:#x} {prog + 0xB000:#x}')
        see_program(img.read_bytes(), prog)
        red = Reduction(marks={'swap': prog + SWAP, 'vbl': prog + VBL, 'go': prog + GO},
                        tally=tuple(prog + a for a in WAIT) + lock)
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
        route.run(['-JOY2_UP'])
    finally:
        subprocess.run([sys.executable, str(ROOT / 'tools/buggyboy.py'), 'quit'], capture_output=True)
    red.save(str(out / 'profile.pkl.gz'))
    chip.save(str(out / 'chip.pkl.gz'))
    (out / 'chip.txt').write_text(chip_report(chip))
    rep = f'slave base {base:06x}, program base {prog:06x}\n' + report(red, lock, prog)
    (out / 'report.txt').write_text(rep)
    print(rep)


def report(red, lock, prog):
    swaps = [e for e in red.events if e[0] == 'swap']
    total = red.total()
    nf = len(red.fields)
    lock_cyc = sum(red.self[pc] for pc in lock)
    lines = [f'fields {nf}  frames (swaps) {len(swaps)}  fps {50 * len(swaps) / nf:.2f}  '
             f'fields/frame {nf / max(1, len(swaps)):.3f}',
             f'traced cycles {total}  waits {red.tallied} ({100 * red.tallied / total:.1f}%): '
             f'slave lock {100 * lock_cyc / total:.1f}%, field wait {100 * (red.tallied - lock_cyc) / total:.1f}%']
    bounds, acc = [], 0
    for f in red.fields:
        acc += f['total']
        bounds.append(acc)
    fidx = [bisect.bisect_right(bounds, e[1]) for e in swaps]
    hist = collections.Counter(b - a for a, b in zip(fidx, fidx[1:]))
    lines.append('fields between swaps: ' + ', '.join(f'{k}:{v}' for k, v in sorted(hist.items())))
    fc = total / nf
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
    for lo in range(0, nf, 50):
        ws = [w for f, w in seq if lo <= f < lo + 50]
        if ws:
            lines.append(f'  {lo:4d}-{lo + 49:4d}  {sum(ws) / len(ws):.3f} / {max(ws):.3f}  ' + '#' * round(5 * max(ws)))
    lines.append('DMA slots: ' + ', '.join(f'{k} {v:.1%}' for k, v in red.dma_shares().items()))
    lines.append('')
    lines.append('self cycles by PC (top 40), % of traced cycles:')
    for pc, c in red.self.most_common(40):
        where = f'+{pc - prog:05x}' if 0 <= pc - prog < 0xB000 else f'{pc:06x}'
        lines.append(f'  {where:>8}  {c:10d}  {100 * c / total:5.1f}%  x{red.counts[pc]}')
    lines.append('')
    lines.append('main-loop routines, inclusive (interrupts that hit them included), % of traced cycles:')
    inc = red.inclusive()
    for off, what in MAIN:
        pc = prog + off
        lines.append(f'  +{off:05x}  x{red.counts[pc]:6d}  {100 * inc[pc] / total:5.1f}%  {what}')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main(sys.argv[1:])
