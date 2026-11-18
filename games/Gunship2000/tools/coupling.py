#!/usr/bin/env python3
"""The coupling test of the AGA flight: coupling.py OUT [REFERENCE...]; coupling.py compare OUT REFERENCE...

Does the simulation depend on the frame rate? Flies the pinned mission (BUILD=verify, or a VERIFY
SLAVE) with the same input at the same game time, and samples the state at equal game time:
run it at the original 6-tick cap and with CUSTOM2=1 (WHD_ARGS=CUSTOM2=1), then compare.

The route is profile_flight's to the cockpit. At mission second 3 (gdb watchpoint on the clock)
and INPUT_DELAY fields (default 0):
F6, 9 (rotor), 10 s, `=` (collective up) for 4 s, the up arrow (cyclic forward) for 3 s, the left
arrow for 1 s. Then at each mission second in SAMPLES the state is read at the two frame starts
around it (the watchpoint on the seconds stops in the frame that crosses it, before the frame's
simulation, code $8e; a breakpoint at code $28 the frame after) and interpolated to the second:

- the player's object (bss+$d348, 136 bytes) as words,
- the position table (bss+$127a, x, y, z longs, POSITIONS entries).

OUT/samples.json holds them. With REFERENCEs (earlier OUTs: the 6-tick cap, INPUT_DELAY 0-3) it
checks the cockpit against the first (profile_flight) and prints the quantities whose samples
fall outside the references' envelope, the worst first, against their range and spread.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profile_flight as P  # noqa: E402
import gs2  # noqa: E402
from gunship2000 import KEYS, Session  # noqa: E402

KEYS.setdefault('=', 0x0c)
SAMPLES = list(range(25, 95, 5))
POSITIONS = 64
PLAYER = 0xd348
TABLE = 0x127a
SECONDS, FRACTION = 0xc682, 0xc684


def state(s, h2):
    b = s.read(h2 + PLAYER, 136)
    out = {f'player+${i:02x}': int.from_bytes(b[i:i + 2], 'big', signed=True) for i in range(0, 136, 2)}
    t = s.read(h2 + TABLE, 12 * POSITIONS)
    for n in range(POSITIONS):
        for j, axis in enumerate('xyz'):
            o = 12 * n + 4 * j
            out[f'pos{n}.{axis}'] = int.from_bytes(t[o:o + 4], 'big', signed=True)
    c = s.read(h2 + SECONDS, 4)
    out['time'] = int.from_bytes(c[:2], 'big') + int.from_bytes(c[2:], 'big') / 65536
    return out


class Watch:
    """Stops on writes to the mission seconds, and at frame starts."""

    def __init__(self, s, layout):
        self.s = s
        self.layout = layout
        self.h0 = layout['hunks']['0']['base']
        self.h2 = layout['hunks']['2']['base']
        s.cmd(f'watch *(unsigned short*){self.h2 + SECONDS:#x}')

    def second(self, n):
        """Run until the frame whose clock add crosses mission second n."""
        while self.s.word(self.h2 + SECONDS) < n:
            self.s.cmd('continue', timeout=600)

    def frame_start(self):
        self.s.cmd('delete')
        self.s.cmd(f'tbreak *{self.h0 + 0x28:#x}')
        self.s.cmd('continue', timeout=600)
        self.s.cmd(f'watch *(unsigned short*){self.h2 + SECONDS:#x}')


def dump(s, w, n, which):
    """With DUMPS=1: the data and BSS hunks raw, OUT/dumps/<second>-<a|b>-<hunk>.bin."""
    if not os.environ.get('DUMPS'):
        return
    d = s.out / 'dumps'
    d.mkdir(exist_ok=True)
    for h in ('1', '2'):
        (d / f'{n}-{which}-{h}.bin').write_bytes(s.read(w.layout['hunks'][h]['base'],
                                                         w.layout['hunks'][h]['size']))


def sample(s, w, n):
    w.second(n)
    dump(s, w, n, 'a')
    a = state(s, w.h2)
    # At code $8e the clock holds the frame's end; the state is still its start.
    dt = s.word(w.h2 + 0xc67e)
    a['time'] -= dt * 15 / 32 / 65536
    w.frame_start()
    dump(s, w, n, 'b')
    b = state(s, w.h2)
    f = (n - a['time']) / (b['time'] - a['time']) if b['time'] > a['time'] else 0.0
    return {k: a[k] + (b[k] - a[k]) * f for k in a if k != 'time'} | {'at': [a['time'], b['time']]}


def fly(out):
    s = Session(out)
    try:
        f = P.Flight(s)
        cockpit = P.route(f)
        layout = gs2.locate(s)
        w = Watch(s, layout)
        w.second(3)
        s.cmd('delete')
        s.fields(int(os.environ.get('INPUT_DELAY', '0')))
        s.tap('f6', hold=10, after=10)
        s.tap('9', hold=10, after=10)
        s.fields(500)
        s.tap('=', hold=200, after=10)
        s.tap('up', hold=150, after=10)
        s.tap('left', hold=50, after=10)
        s.cmd(f'watch *(unsigned short*){w.h2 + SECONDS:#x}')
        samples = {}
        for n in SAMPLES:
            samples[n] = sample(s, w, n)
            print(n, samples[n]['at'], flush=True)
        s.cmd('delete')
        f.shot('end')
        env = {k: s.env.get(k, os.environ.get(k)) for k in ('SETUP', 'EXTRA_ARGS', 'SLAVE', 'BUILD', 'WHD_ARGS',
                                                             'INPUT_DELAY')}
        (s.out / 'samples.json').write_text(json.dumps(dict(env=env, samples=samples), indent=1))
        return cockpit
    finally:
        s.quit()


def compare(out, references):
    """Per quantity: how far the run's samples fall outside the envelope of the references'
    (the same inputs a field or more apart: a turn's heading alone spreads by 4 degrees)."""
    a = json.loads((Path(out) / 'samples.json').read_text())['samples']
    rs = [json.loads((Path(r) / 'samples.json').read_text())['samples'] for r in references]
    keys = [k for k in rs[0][next(iter(rs[0]))] if k != 'at']
    rows = []
    for k in keys:
        lo = {n: min(r[n][k] for r in rs) for n in rs[0]}
        hi = {n: max(r[n][k] for r in rs) for n in rs[0]}
        span = max(hi.values()) - min(lo.values())
        out_by = [max(0.0, lo[n] - a[n][k], a[n][k] - hi[n]) for n in rs[0]]
        if span == 0 and not any(out_by):
            continue
        worst = max(out_by)
        if worst == 0:
            continue
        spread = max(hi[n] - lo[n] for n in rs[0])
        rows.append((worst / span if span else float('inf'), k, worst, span, spread, out_by))
    rows.sort(key=lambda x: -x[0])
    print(f'{len(keys)} quantities against {len(rs)} reference runs; outside their envelope:')
    print(f'{"quantity":14} {"outside":>10} {"ref range":>11} {"ref spread":>11}  by second {", ".join(rs[0])}')
    for rel, k, worst, span, spread, out_by in rows:
        print(f'{k:14} {worst:10.1f} {span:11.1f} {spread:11.1f}  ' + ' '.join(f'{d:.0f}' for d in out_by))
    return rows


def main(out, *references):
    cockpit = fly(out)
    if references:
        d, same = P.same_mission(cockpit, references[0])
        print(f'cockpit against {references[0]}: mean difference {d:.2f}', flush=True)
        if not same:
            raise SystemExit(f'not the reference mission (difference {d:.2f}); BUILD=verify?')
        compare(out, references)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == 'compare':
        compare(sys.argv[2], sys.argv[3:])
    else:
        main(*sys.argv[1:])
