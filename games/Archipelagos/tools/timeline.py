#!/usr/bin/env python3
"""The frame on the beam: where each phase of a frame starts and how long it takes.

    python3 tools/timeline.py OUT [FIELDS]

Needs a server on a CPU that records an instruction trace (SETUP=a1200-030
EXTRA_ARGS=--uae_mmu_model=0, or the a500), with the game where it should be measured
(tools/route.py). Traces FIELDS fields (default 8) from there and writes OUT/timeline.txt
(also printed): for each phase of each frame, the field and the line it starts at, its length
in lines, the lines the CPU spent in the game's blitter wait and outside the program (the
slave, WHDLoad: on a 68020+ the slave's blitter wait and border clear), and the blitter's
DMA slots in it. The phases, by the first instruction of each (docs/internals.md, the frame):

    render  the renderer (the frame-counted steps, then the field wait)
    draw    after the renderer's field wait
    view    draw view
    sky     the sky fill
    objs    the objects (from the sky fill's return)
    border  the border clear
    swap    the swap
    world   the world update

A line is 227 DMA slots; a field 313 lines (PAL) or 263 (NTSC). SPS 628 with VARIANT=ArchipelagosNTSC.
"""
import bisect
import collections
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
import route  # noqa: E402
from amigaxdev import barto  # noqa: E402

if route.US:
    PHASES = {0x11d7e: 'render', 0x11da2: 'draw', 0x11e2a: 'view', 0xae3e: 'sky',
              0x11dbc: 'objs', 0xb7fe: 'border', 0x124c8: 'swap', 0xf74a: 'world'}
    WAIT, END = (0x121b2, 0x121c4), 0x1469c
else:
    PHASES = {0x11ac6: 'render', 0x11aea: 'draw', 0x11b72: 'view', 0xae32: 'sky',
              0x11b04: 'objs', 0xb7f0: 'border', 0x12210: 'swap', 0xf6f6: 'world'}
    WAIT, END = (0x11efa, 0x11f0c), 0x142f8
LINE = 227


def timeline(trace, body):
    t = barto.load(trace)
    ev, wait, out, blit = [], collections.Counter(), collections.Counter(), []
    slots = None
    for f in t.fields:
        d = bytes(f.dma)
        # the records cover 313 lines; a field has as many as have refresh slots (NTSC 263)
        n = max(i for i in range(0, len(d) // f.dma_size, LINE) if 1 in
                d[i * f.dma_size + 29:(i + LINE) * f.dma_size:f.dma_size]) + LINE
        slots = slots or n
        per = f.cycles / n
        c, base = 0, f.index * n
        for pc, cost, _ in t.instructions(f):
            s = base + c / per
            c += cost or 0
            if pc is None or pc == 0x7fffffff:
                continue
            o = pc - body
            if o in PHASES and (not ev or ev[-1][1] != PHASES[o]):
                ev.append((s, PHASES[o]))
            if ev and WAIT[0] <= o < WAIT[1]:
                wait[len(ev) - 1] += (cost or 0) / per
            elif ev and not 0 <= o < END:
                out[len(ev) - 1] += (cost or 0) / per
        blit += [base + i for i in range(n) if d[i * f.dma_size + 29] == 5]
    lines = []
    for i, (s, name) in enumerate(ev):
        e = ev[i + 1][0] if i + 1 < len(ev) else len(t.fields) * slots
        nb = bisect.bisect_left(blit, e) - bisect.bisect_left(blit, s)
        if name == 'render':
            lines.append('')
        lines.append(f'{name:7} {int(s // slots):3}:{(s % slots) / LINE:5.1f}  {(e - s) / LINE:6.1f} lines'
                     f'  blitter wait {wait[i] / LINE:5.1f}  outside {out[i] / LINE:5.1f}'
                     f'  blitter {nb:6d} slots')
    return '\n'.join(lines).lstrip('\n') + '\n'


def report(trace, body):
    return f'body ${body:X}; field:line, lengths in lines ({LINE} slots)\n' + timeline(trace, body)


def main(args):
    if not args:
        sys.exit(__doc__)
    out = Path(args[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    n = int(args[1]) if len(args) > 1 else 8
    body = route.body()
    p = out / 'trace.bin'
    route.req('profile', str(n), str(p))
    text = report(p, body)
    p.unlink()
    (out / 'timeline.txt').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main(sys.argv[1:])
