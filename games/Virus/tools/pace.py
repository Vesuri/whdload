#!/usr/bin/env python3
"""Game time against elapsed fields: ticks and drawn frames a second in the demo.

    python3 tools/pace.py [FIELDS [CHUNK]]

Needs a server just booted with tools/boot.sh. Runs to the demo's start ($641fe), past its
fade-in (the first main loop pass's end, $6434c) and to the next field (tools/codebase.py
`to_window`), then FIELDS fields (default 1250) in CHUNK-field steps (default 50), reading
after each the game's frame counter $c9f4 (one a main loop pass: a tick) and, with Enhanced
framerate on, the slave's _frames (passes that drew) and _period (fields a tick). The
slave's address is the jsr target at $64214 (_pass); the variables' offsets come from the
release build's listing (tmp/build/release/Virus.lst). Without the patch every pass draws.
The demo is a recording of 1189 ticks from there: a machine at 50 fps plays it in about
1190 fields, so the window ends early with the last chunk that was all demo.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
from game_server import game_server  # noqa: E402
sys.path.insert(0, str(ROOT / 'tools'))
import codebase  # noqa: E402


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

    d = codebase.delta(srv)
    print(f'code at ${0x57000 + d:x}')
    codebase.to_window(srv, d)
    enhanced = peek(0x64212 + d, 2) == 0x4eb9
    if enhanced:
        sym = symbols()
        base = peek(0x64214 + d, 4) - sym['_pass']
        period = peek(base + sym['_period'], 4)
        frames = lambda: peek(base + sym['_frames'], 4)  # noqa: E731
        print(f'Enhanced framerate: a tick every {period} fields ({50 / period:.2f} Hz)')
    else:
        period, frames = None, None
        print('original: one tick a drawn frame')
    t0 = peek(codebase.at(0xc9f4, d), 2)
    f0 = frames() if frames else 0
    done = 0
    rows = []
    while done < total:
        n = min(step, total - done)
        srv.request(f'fields {n}')
        done += n
        t, f = peek(codebase.at(0xc9f4, d), 2) - t0, (frames() - f0) if frames else None
        rows.append((done, t, f if f is not None else t))
    prev = (0, 0, 0)
    for d, t, f in rows:
        print(f'  {d:5d} fields: ticks {t:4d} ({50 * (t - prev[1]) / (d - prev[0]):5.1f}/s), '
              f'drawn {f:4d} ({50 * (f - prev[2]) / (d - prev[0]):5.1f}/s)')
        prev = (d, t, f)
    # The demo is a recording of a fixed length (1189 ticks from the fade-in's end); a
    # machine at 50 fps ends it inside the window, then the attract screen counts no ticks.
    # The window ends with the last chunk a later chunk's ticks show was all demo.
    last = len(rows) - 1
    if len(rows) > 1 and rows[-1][1] == rows[-2][1]:
        last = max(i for i in range(len(rows) - 1) if rows[i + 1][1] > rows[i][1])
        print(f'the demo ended after {rows[last][0]} to {rows[last + 1][0]} fields: '
              f'the window ends at {rows[last][0]}')
    d, t, f = rows[last]
    nominal = f', nominal {d / period:.1f} ({100 * t * period / d:.1f}%)' if period else ''
    print(f'{d} fields: {t} ticks ({50 * t / d:.2f}/s{nominal}), {f} drawn ({50 * f / d:.2f} fps)')


if __name__ == '__main__':
    main(sys.argv[1:])
