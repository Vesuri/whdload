#!/usr/bin/env python3
"""Game time against frames: a move and the renderer's steps, field by field.

    python3 tools/timecheck.py OUT [FIELDS]
    python3 tools/timecheck.py OUT effects

Needs a server just booted with tools/boot.sh (any setup). Runs tools/route.py's 'start',
holds the left button 4 fields (a move to the cell ahead), then reads the game's clocks
after every field for FIELDS fields (default 300): the field counter, the back buffer, the
position, the terrain animation phase, an object animation timer and the world tick
countdown (SPS 628's with VARIANT=ArchipelagosNTSC, as for tools/route.py). Writes
OUT/state.tsv and prints:

- frames shown (flips of the back buffer) and fps;
- the move: the fields from the first change of the position to the last, and the frames
  shown in between;
- the renderer's steps (the terrain phase's changes; 9 to 0, a step each) and world ticks
  (reloads of the countdown), each a second.

Compare two slaves on one setup by their frame sequences: OUT/frames.tsv has the clocks at
each frame shown (the field after a flip).

`effects` plays archipelago 1 to its end instead (tools/play.py): both stones,
then the Obelisk, reading tools/play.py's CLOCKS every field from the first interactive
one to 700 fields after the Obelisk's click. Writes OUT/effects.tsv and prints, for each
stone's collapse (the six-frame effect: its count at offset $12B96 non-zero) and for the
Obelisk's two ramps (offsets $CF1C, $CF1E non-zero), the fields and frames it took.
"""
import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import route  # noqa: E402

BASE = 0x14800       # one dump covers every variable: $14800-$14e00 in SPS 627
SIZE = 0x600
VARS = [  # (name, SPS 627 address, size, signed); SPS 628's are route.VARS higher
    ('fields', 0x1487e, 4, False),
    ('back', 0x14886, 4, False),
    ('x', 0x149da, 2, False),
    ('y', 0x149dc, 2, False),
    ('phase', 0x14dc8, 2, True),
    ('timer', 0x14dd4, 2, True),
    ('tick', 0x149d2, 2, True),
]


def effects(out):
    import play
    route.run(['start'])
    play.record()
    play.stones(log=lambda s: None)
    play.obelisk(log=lambda s: None)
    play.fields(700)
    rows = play.RECORD
    names = [c[0] for c in play.CLOCKS]
    with open(out / 'effects.tsv', 'w') as f:
        f.write('\t'.join(names) + '\n')
        for r in rows:
            f.write('\t'.join(str(v) for v in r) + '\n')
    col = {k: i for i, k in enumerate(names)}
    flips = {i for i in range(1, len(rows)) if rows[i][col['back']] != rows[i - 1][col['back']]}

    def spans(on):
        out, start = [], None
        for i, r in enumerate(rows):
            if on(r) and start is None:
                start = i
            elif not on(r) and start is not None:
                out.append((start, i))
                start = None
        return out

    print(f'{len(rows)} fields, {len(flips)} frames')
    for name, on in (('stone', lambda r: r[col['stone']]),
                     ('ramps', lambda r: r[col['ramp1']] or r[col['ramp2']])):
        for a, b in spans(on):
            print(f'{name}: fields {a}-{b - 1} ({b - a} fields), '
                  f'{sum(1 for i in flips if a < i <= b)} frames')


def main(args):
    if not args:
        sys.exit(__doc__)
    if args[1:] == ['effects']:
        out = Path(args[0]).resolve()
        out.mkdir(parents=True, exist_ok=True)
        return effects(out)
    out = Path(args[0]).resolve()
    n = int(args[1]) if len(args) > 1 else 300
    shift = route.VARS
    hz = 60 if route.US else 50   # the NTSC variant boots an NTSC machine (game.conf)
    out.mkdir(parents=True, exist_ok=True)
    route.run(['start'])
    dump = out / 'dump.bin'
    rows = []
    route.req('gdb', 'monitor input JOY1_FIRE_BUTTON 1')
    for i in range(n):
        if i == 4:
            route.req('gdb', 'monitor input JOY1_FIRE_BUTTON 0')
        route.req('gdb', 'monitor fields 1')
        route.req('gdb', f'dump binary memory {dump} {BASE + shift:#x} {BASE + shift + SIZE:#x}')
        d = dump.read_bytes()
        rows.append([int.from_bytes(d[a - BASE:a - BASE + s], 'big', signed=sg)
                     for _, a, s, sg in VARS])
    dump.unlink()
    names = [v[0] for v in VARS]
    with open(out / 'state.tsv', 'w') as f:
        f.write('\t'.join(names) + '\n')
        for r in rows:
            f.write('\t'.join(str(v) for v in r) + '\n')
    col = {k: i for i, k in enumerate(names)}
    flips = [i for i in range(1, n) if rows[i][col['back']] != rows[i - 1][col['back']]]
    with open(out / 'frames.tsv', 'w') as f:
        f.write('field\t' + '\t'.join(names[2:]) + '\n')
        for i in flips:
            f.write(f'{i}\t' + '\t'.join(str(v) for v in rows[i][2:]) + '\n')
    pos = [(r[col['x']], r[col['y']]) for r in rows]
    moved = [i for i in range(1, n) if pos[i] != pos[i - 1]]
    steps = sum(1 for i in range(1, n) if rows[i][col['phase']] != rows[i - 1][col['phase']])
    ticks = sum(1 for i in range(1, n) if rows[i][col['tick']] > rows[i - 1][col['tick']])
    secs = n / hz
    print(f'{n} fields: {len(flips)} frames, {len(flips) / secs:.2f} fps')
    if moved:
        a, b = moved[0], moved[-1]
        fr = sum(1 for i in flips if a <= i <= b)
        print(f'move: fields {a}-{b} ({b - a + 1} fields), {fr} frames; '
              f'{pos[a - 1]} -> {pos[b]}')
    else:
        print('move: none')
    print(f'renderer steps {steps} ({steps / secs:.2f} a second), '
          f'world ticks {ticks} ({ticks / secs:.2f} a second)')


if __name__ == '__main__':
    main(sys.argv[1:])
