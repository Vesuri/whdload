#!/usr/bin/env python3
"""The AGA game's passes and frames, walking: rr_passes.py OUT [EVENTS] (docs/performance.md)

rr_prof.py's workload (its Session: the direct start, the avion.DO open, 150 fields, then
keypad 9 held; the run options through the environment) with gdb breakpoints in hunk 1
instead of a profile: the frame routine's entry (+$49b2, P), the pass's start after the
cap wait (+$49f6, p), the 3D view's drawing (+$a478, D) and the swap (+$4b30, S), each
event with the VBL count (+$ee6c) and the beam's line. EVENTS events (default 240) after
50 fields of walking. Prints the drawing passes in fields (a D pass's p to its S, with the
line as a fraction of 313), the frame intervals (D to D, in fields), the frames per 500
fields at that rate and the event log; OUT/passes.json keeps the events.

Breakpoints stop the emulation, not its time: the counts are those of the run itself.
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_prof import Session, find_hunk0, hunks, layout  # noqa: E402

MARKS = {0x49b2: 'P', 0x49f6: 'p', 0xa478: 'D', 0x4b30: 'S'}
VBL = 0xee6c
LINES = 313


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 240
    s = Session(out)
    try:
        if s.env['VARIANT'] != 'RobinsonsRequiemAGA':
            raise SystemExit('the AGA game only')
        base = None
        while base is None:
            if s.field > 3000:
                raise TimeoutError('START hunk 0 not found in 3000 fields')
            s.fields(10)
            try:
                base = find_hunk0(s.g, s.env['VARIANT'])
            except RuntimeError:
                pass
        open_at = base + layout(s.env['VARIANT'])['calls']['open']
        s.cmd(f'break *{open_at:#x}')
        s.cmd('condition $bpnum *(unsigned int *)$d1 == 0x6176696f')
        s.g.cmd('continue', timeout=1200)
        s.cmd('delete')
        s.fields(150)
        h1 = hunks(s, base)[1]
        s.cmd('monitor key 3f 1')
        s.fields(50)
        marks = {h1 + o: m for o, m in MARKS.items()}
        for a in marks:
            s.cmd(f'break *{a:#x}')
        ev = []
        for _ in range(n):
            s.g.cmd('continue', timeout=300)
            pc = int(s.g.cmd('info registers pc').split()[1], 16)
            vbl = int.from_bytes(s.read(h1 + VBL, 4), 'big')
            line = (int.from_bytes(s.read(0xdff004, 4), 'big') >> 8) & 0x1ff
            ev.append((marks.get(pc, hex(pc)), vbl, line))
        s.cmd('delete')
        s.cmd('monitor key 3f 0')
    finally:
        s.quit()
    t0 = ev[0][1]
    passes, draws, start, drawing = [], [], None, False
    for m, v, line in ev:
        t = v + line / LINES
        if m == 'p':
            start, drawing = t, False
        elif m == 'D':
            drawing = True
            draws.append(v)
        elif m == 'S' and drawing and start is not None:
            passes.append(t - start)
            drawing = False
    gaps = [b - a for a, b in zip(draws, draws[1:])]
    print('drawing pass fields:', ' '.join(f'{x:.2f}' for x in sorted(passes)))
    print('frame intervals:', dict(sorted(collections.Counter(gaps).items())),
          f'mean {sum(gaps) / len(gaps):.2f}, {500 * len(gaps) / sum(gaps):.1f} frames '
          'per 500 fields' if gaps else '')
    print('events:', ' '.join(f'{m}{v - t0}.{line}' for m, v, line in ev))
    (out / 'passes.json').write_text(json.dumps(dict(env=s.env, events=ev)) + '\n')


if __name__ == '__main__':
    main()
