#!/usr/bin/env python3
"""The drawn frames of the flight (VARIANT, default the AGA version): screens.py OUT [REFERENCE]; screens.py compare OUT REFERENCE

Flies profile_flight's route to the cockpit and stops at every present (AGA code $129c4) for FRAMES
frames (default 30) in each of three views: the cockpit as it starts, F5 (chase), F6 (tactical).
At the present B+$b8dc is the screen just drawn; its 32000 bytes (four interleaved planes, rows
of 160 bytes) go to OUT/screens/<view>-<frame>.bin, their SHA-256 to OUT/screens.json.

For P5c, renderer patches that must draw the same pixels: at the 6-tick cap (no CUSTOM2), on the
a1200-030, where every frame takes the cap's 6 ticks, the same build and inputs give the same
frames. With REFERENCE (an earlier OUT) the frames are compared one by one: the first differing
frame of each view, and per differing frame the bytes and the lines that differ.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profile_flight as P  # noqa: E402
import gs2  # noqa: E402
from gunship2000 import Session  # noqa: E402

PRESENT = gs2.O['present']
DRAWN = gs2.O['drawn']
SIZE = 32000
VIEWS = (('cockpit', None), ('f5', 'f5'), ('f6', 'f6'))


def capture(s, h0, h2, view, n, out):
    d = out / 'screens'
    d.mkdir(exist_ok=True)
    sums = []
    s.cmd(f'break *{h0 + PRESENT:#x}')
    for i in range(n):
        s.cmd('continue', timeout=600)
        b = s.read(s.long(h2 + DRAWN), SIZE)
        (d / f'{view}-{i:03d}.bin').write_bytes(b)
        sums.append(hashlib.sha256(b).hexdigest())
    s.cmd('delete')
    return sums


def fly(out):
    s = Session(out)
    try:
        f = P.Flight(s)
        cockpit = P.route(f)
        layout = gs2.locate(s)
        h0, h2 = layout['hunks']['0']['base'], layout['hunks']['2']['base']
        n = int(os.environ.get('FRAMES', '30'))
        frames = {}
        for view, key in VIEWS:
            if key:
                s.tap(key, hold=10, after=10)
            frames[view] = capture(s, h0, h2, view, n, s.out)
            print(view, len(frames[view]), flush=True)
        env = {k: s.env.get(k, os.environ.get(k)) for k in ('SETUP', 'EXTRA_ARGS', 'SLAVE', 'BUILD', 'WHD_ARGS')}
        (s.out / 'screens.json').write_text(json.dumps(dict(env=env, frames=frames), indent=1))
        return cockpit
    finally:
        s.quit()


def compare(out, reference):
    a = json.loads((Path(out) / 'screens.json').read_text())['frames']
    r = json.loads((Path(reference) / 'screens.json').read_text())['frames']
    same = True
    for view in r:
        diff = [i for i, (x, y) in enumerate(zip(a.get(view, []), r[view])) if x != y]
        n = min(len(a.get(view, [])), len(r[view]))
        print(f'{view}: {n - len(diff)} of {n} frames the same')
        for i in diff[:5]:
            x = (Path(out) / 'screens' / f'{view}-{i:03d}.bin').read_bytes()
            y = (Path(reference) / 'screens' / f'{view}-{i:03d}.bin').read_bytes()
            bytes_ = [j for j in range(SIZE) if x[j] != y[j]]
            lines = sorted({j // 160 for j in bytes_})
            print(f'  frame {i}: {len(bytes_)} bytes on {len(lines)} lines, from line {lines[0]}, '
                  f'first at byte {bytes_[0]} (plane {bytes_[0] % 160 // 40})')
        same = same and not diff and n == len(r[view])
    return same


def main(out, reference=None):
    cockpit = fly(out)
    if reference:
        d, same = P.same_mission(cockpit, reference)
        print(f'cockpit against {reference}: mean difference {d:.2f}', flush=True)
        if not same:
            raise SystemExit(f'not the reference mission (difference {d:.2f}); BUILD=verify?')
        if not compare(out, reference):
            raise SystemExit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == 'compare':
        sys.exit(0 if compare(sys.argv[2], sys.argv[3]) else 1)
    main(*sys.argv[1:])
