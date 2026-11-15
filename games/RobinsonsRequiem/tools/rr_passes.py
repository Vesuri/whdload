#!/usr/bin/env python3
"""The game's passes and frames, walking: rr_passes.py OUT [EVENTS] (docs/performance.md)

rr_prof.py's workload (its Session: the direct start, the avion open, 150 fields, then
keypad 9 held; the run options through the environment, VARIANT=RobinsonsRequiem for the
ECS game) with gdb breakpoints in hunk 1 instead of a profile: the frame routine's entry
(AGA +$49b2, ECS +$3076: P), the pass's start after the cap wait (+$49f6, +$30ba: p), the
3D view's drawing (+$a478, +$8ae2: D), the swap (+$4b30, +$31f4: S) and the list's start
(+$251a, +$cbe, with d5 0: L; every pass, in the AGA game a catch-up pass since plan step 7
an L without a P, and since plan step 11 a p without a P is a presentation frame's
routine), each event with the VBL count (+$ee6c, +$d4c2) and the beam's line. The ECS
game's frame routine and MAIN loop are the AGA's instruction for instruction. KEY=hex the
raw key held (default 3f, keypad 9; 3e walks; none for no key). A D event also has the
view's camera, as the drawing sees it (a2's +22/24/26 and +52/54/56). EVENTS events
(default 240) after 50 fields of walking. Prints the drawing passes in fields (a D pass's p
to its S, with the line as a fraction of 313), the frame intervals (D to D, in fields), the
frames per 500 fields at that rate, the intervals of the fields the frames show in (an S
before line 310 shows in the next field, from line 310 the one after: the copper takes the
pointers at the field's start, docs/internals.md, "AGA improvements", item 11), the
passes, frame routines and catch-up passes, and the event log; OUT/passes.json keeps the
events.

Breakpoints stop the emulation, not its time: the counts are those of the run itself.
"""
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_prof import Session, hunks  # noqa: E402

# hunk 1: the events and the VBL count
SITES = {'RobinsonsRequiemAGA': ({0x49b2: 'P', 0x49f6: 'p', 0xa478: 'D', 0x4b30: 'S',
                                  0x251a: 'L'}, 0xee6c),
         'RobinsonsRequiem': ({0x3076: 'P', 0x30ba: 'p', 0x8ae2: 'D', 0x31f4: 'S',
                               0xcbe: 'L'}, 0xd4c2)}
LINES = 313
SHOWN_BY = 310      # a swap from this line on shows a field later (_swap)


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 240
    key = os.environ.get('KEY', '3f')
    s = Session(out)
    try:
        sites, vbl_at = SITES[s.env['VARIANT']]
        base = s.to_open()[0]
        s.fields(150)
        h1 = hunks(s, base)[1]
        if key != 'none':
            s.cmd(f'monitor key {key} 1')
        s.fields(50)
        marks = {h1 + o: m for o, m in sites.items()}
        for a in marks:
            s.cmd(f'break *{a:#x}')
            if marks[a] == 'L':
                s.cmd('condition $bpnum ($d5 & 0xffff) == 0')
        ev = []
        for _ in range(n):
            s.g.cmd('continue', timeout=300)
            pc = int(s.g.cmd('info registers pc').split()[1], 16)
            vbl = int.from_bytes(s.read(h1 + vbl_at, 4), 'big')
            line = (int.from_bytes(s.read(0xdff004, 4), 'big') >> 8) & 0x1ff
            m = marks.get(pc, hex(pc))
            if m == 'D':
                a2 = int(s.g.cmd('info registers a2').split()[1], 16)
                b = s.read(a2, 58)
                cam = [int.from_bytes(b[o:o + 2], 'big', signed=True) for o in (22, 24, 26, 52, 54, 56)]
                ev.append((m, vbl, line, cam))
            else:
                ev.append((m, vbl, line))
        s.cmd('delete')
        if key != 'none':
            s.cmd(f'monitor key {key} 0')
    finally:
        s.quit()
    t0 = ev[0][1]
    passes, draws, start, drawing = [], [], None, False
    for m, v, line, *_ in ev:
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
    shown = [v + 1 + (line >= SHOWN_BY) for m, v, line, *_ in ev if m == 'S']
    sgaps = [b - a for a, b in zip(shown, shown[1:])]
    print('drawing pass fields:', ' '.join(f'{x:.2f}' for x in sorted(passes)))
    print('frame intervals:', dict(sorted(collections.Counter(gaps).items())),
          f'mean {sum(gaps) / len(gaps):.2f}, {500 * len(gaps) / sum(gaps):.1f} frames '
          'per 500 fields' if gaps else '')
    print('shown intervals:', dict(sorted(collections.Counter(sgaps).items())),
          f'mean {sum(sgaps) / len(sgaps):.2f}' if sgaps else '')
    cnt = collections.Counter(e[0] for e in ev)
    print(f"passes {cnt['L']}, frame routines {cnt['P']}, catch-up passes {cnt['L'] - cnt['P']}, "
          f"presentation frame routines {cnt['p'] - cnt['P']}, in {ev[-1][1] - t0} fields")
    cams = [(e[1], e[3]) for e in ev if e[0] == 'D']
    print('cameras (field: x y z, angles):', ' '.join(f'{v - t0}:{",".join(map(str, c))}' for v, c in cams))
    print('events:', ' '.join(f'{e[0]}{e[1] - t0}.{e[2]}' for e in ev))
    (out / 'passes.json').write_text(json.dumps(dict(env=s.env, events=ev)) + '\n')


if __name__ == '__main__':
    main()
