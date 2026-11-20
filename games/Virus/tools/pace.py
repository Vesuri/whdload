#!/usr/bin/env python3
"""Game time against elapsed fields: ticks and drawn frames a second in the demo.

    python3 tools/pace.py [FIELDS [CHUNK]]

Needs a server just booted with tools/boot.sh. Runs to the demo's start ($641fe), then
FIELDS fields (default 1250) in CHUNK-field steps (default 50), reading after each the
game's frame counter $c9f4 (one a main loop pass: a tick) and, with Enhanced framerate on,
the slave's _frames (passes that drew) and _period (fields a tick). The slave's address is
the jsr target at $64214 (_pass); the variables' offsets come from the release build's
listing (tmp/build/release/Virus.lst). Without the patch every pass draws.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
from game_server import game_server  # noqa: E402


def symbols():
    lst = (ROOT / 'tmp/build/release/Virus.lst').read_text(encoding='latin-1')
    return {m[1]: int(m[2], 16) for m in re.finditer(r'^(_\w+)\s+00:([0-9A-F]{8})$', lst, re.M)}


def main(args):
    total = int(args[0]) if args else 1250
    step = int(args[1]) if len(args) > 1 else 50
    srv = game_server('virus')

    def peek(addr, n):
        txt = srv.request(f'peek {addr:x} {n}')
        return int(next(w for w in txt.split() if len(w) == 2 * n), 16)

    srv.request('until 0x641fe')
    enhanced = peek(0x64212, 2) == 0x4eb9
    if enhanced:
        sym = symbols()
        base = peek(0x64214, 4) - sym['_pass']
        period = peek(base + sym['_period'], 4)
        frames = lambda: peek(base + sym['_frames'], 4)  # noqa: E731
        print(f'Enhanced framerate: a tick every {period} fields ({50 / period:.2f} Hz)')
    else:
        period, frames = None, None
        print('original: one tick a drawn frame')
    t0 = peek(0xc9f4, 2)
    f0 = frames() if frames else 0
    done = 0
    rows = []
    while done < total:
        n = min(step, total - done)
        srv.request(f'fields {n}')
        done += n
        t, f = peek(0xc9f4, 2) - t0, (frames() - f0) if frames else None
        rows.append((done, t, f if f is not None else t))
    prev = (0, 0, 0)
    for d, t, f in rows:
        print(f'  {d:5d} fields: ticks {t:4d} ({50 * (t - prev[1]) / (d - prev[0]):5.1f}/s), '
              f'drawn {f:4d} ({50 * (f - prev[2]) / (d - prev[0]):5.1f}/s)')
        prev = (d, t, f)
    d, t, f = rows[-1]
    nominal = f', nominal {d / period:.1f} ({100 * t * period / d:.1f}%)' if period else ''
    print(f'{d} fields: {t} ticks ({50 * t / d:.2f}/s{nominal}), {f} drawn ({50 * f / d:.2f} fps)')


if __name__ == '__main__':
    main(sys.argv[1:])
