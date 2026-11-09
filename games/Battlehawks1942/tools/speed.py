#!/usr/bin/env python3
"""Game speed against real time, from flight records (tools/record.sh, src/tape.s).
  speed.py [--skip FRAMES] [--hz 50|60] DIR [DIR...]
Each record holds, per flight frame (at its key read, before its step): the VERTB count,
T (10184(a4)), the player's (object 0) x, y, z, heading, roll, pitch and speed word, and
BH's frame counter.  Printed per record:
- frames, fields, frames per second and the T seen;
- game time / real time: a step is 1/T seconds of game time (the steps' sum against the
  fields between the first and last record); 1.000 is real time;
- game time / real time from the second second on (the flight's first frames step by the
  mission's T before the frame average is known);
- distance flown (x, y, z) per real second, to compare machines;
- the turn: heading rate (degrees per real second, 65536 = 360) against the roll, in
  10-degree bins, to compare machines (equal when the turn follows real time).
- with --at: the player's heading, roll, altitude and position at those seconds after the
  first flight frame (the tape's TAPE_TIME build gives every machine the same input in real
  time, so with game time following real time the flights agree).
--skip: frames left out at the start.  Records end where the plane stops moving (the sea).
"""
import argparse, math, struct
from collections import defaultdict
from pathlib import Path

REC = struct.Struct('>HHlllHhhHH')
SIZE = 28


def load(d):
    b = (Path(d) / 'record.bin').read_bytes()
    return [REC.unpack_from(b, o) for o in range(0, len(b) - SIZE + 1, SIZE)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--skip', type=int, default=0)
    p.add_argument('--at', default='')
    p.add_argument('--hz', type=int, default=50)
    p.add_argument('dirs', nargs='+')
    a = p.parse_args()
    for d in a.dirs:
        rows = [r for r in load(d) if r[1]]
        t0 = rows[0][0] if rows else 0
        for n in range(1, len(rows) - 3):
            if all(rows[k][2:5] == rows[n][2:5] for k in range(n + 1, n + 4)):
                rows = rows[:n + 1]
                break
        rows = rows[a.skip:]
        machine = (Path(d) / 'machine.txt').read_text().strip() if (Path(d) / 'machine.txt').exists() else ''
        if len(rows) < 2:
            print(f'{d}: {len(rows)} frames')
            continue
        fields = (rows[-1][0] - rows[0][0]) & 0xffff
        real = fields / a.hz
        game = sum(1 / r[1] for r in rows[:-1])
        ts = sorted({r[1] for r in rows})
        dist = sum(math.dist(q[2:5], r[2:5]) for r, q in zip(rows, rows[1:]))
        print(f'{d} [{machine}]: {len(rows) - 1} frames in {fields} fields, '
              f'{(len(rows) - 1) / real:.1f} fps, T {ts[0]}..{ts[-1]}')
        print(f'  game time / real time {game / real:.4f}')
        late = [r for r in rows if ((r[0] - rows[0][0]) & 0xffff) >= a.hz]
        if len(late) > 1:
            lf = (late[-1][0] - late[0][0]) & 0xffff
            print(f'  game time / real time after the first second {sum(1 / r[1] for r in late[:-1]) / (lf / a.hz):.4f}')
        print(f'  distance flown {dist / real:.1f} units/s')
        bins = defaultdict(lambda: [0.0, 0])
        for r, q in zip(rows, rows[1:]):
            f = (q[0] - r[0]) & 0xffff
            if not f:
                continue
            dh = (q[5] - r[5] + 0x8000) % 0x10000 - 0x8000
            roll = r[6] * 360 / 65536
            b = bins[int(math.floor(roll / 10))]
            b[0] += dh * 360 / 65536
            b[1] += f
        for t in [float(x) for x in a.at.split(',') if x]:
            f = t0 + round(t * a.hz)
            r = next((r for r in rows if ((r[0] - f) & 0xffff) < 0x8000), None)
            if r is None:
                print(f'  {t:5.1f} s: past the record')
                continue
            print(f'  {t:5.1f} s (field +{(r[0] - t0) & 0xffff}): heading {r[5] * 360 / 65536:6.1f} '
                  f'roll {r[6] * 360 / 65536:+6.1f} altitude {r[4]:6d} x {r[2]} y {r[3]}')
        print('  roll      heading deg/s  fields')
        for k in sorted(bins):
            deg, f = bins[k]
            if f >= a.hz:
                print(f'  {k * 10:+4d}..{k * 10 + 10:+4d}  {deg * a.hz / f:+10.2f}  {f:6d}')


if __name__ == '__main__':
    main()
