#!/usr/bin/env python3
"""Vroom's gdb-stub server: the shared commands (docs/running.md) plus

  decrunch <n> [<seconds>]   stop after each of the next n file decrunches (the loader's return
                             from the slave's Decrunch hook at $1CFC8) and report the destination
                             ($1D90E) and decrunched length ($34F32); gives up after <seconds>
                             of emulated running (default 600) without one

    python3 tools/vroom.py serve       (SETUP=, VARIANT=, WARP=1 WINDOW=none, ... as make run)
    python3 tools/vroom.py decrunch 20
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

LOADER_RETURN = 0x1CFC8   # after `jsr $1D0F8` (the slave's Decrunch) in the loader
DEST = 0x1D90E            # decrunch destination
LENGTH = 0x34F32          # decrunched length


def word(g, expr):
    out = g.cmd(f'x/1xw {expr}')
    return int(out.rsplit(':', 1)[1].split()[0], 16)


def decrunch(server, g, rest):
    args = rest.split()
    n = int(args[0]) if args else 1
    timeout = float(args[1]) if len(args) > 1 else 600
    g.stop()
    g.cmd(f'break *{LOADER_RETURN:#x}')
    lines = []
    try:
        for _ in range(n):
            out = g.cmd('continue', timeout=timeout)
            if 'Breakpoint' not in out:
                lines.append('no decrunch: ' + out.strip().splitlines()[-1])
                break
            dest, length = word(g, DEST), word(g, LENGTH)
            lines.append(f'dest ${dest:X} length ${length:X} end ${dest + length:X}')
    finally:
        g.cmd('delete')
        g.cont()
    return '\n'.join(lines)


FIELDS = 0xA884           # the VBL's field counter (long)
BUFFER = 0x86DE           # draw-buffer index, 0 or 4, toggled once per frame at $12FA6
CLOCK = 0x8500            # race clock (long, +2 per field while it runs: centiseconds)
POS = 0xDC50              # the player's distance along the track (long)
STEP = 0xDC60             # the player's last step (word), as added to POS at $C782/$C7C2


def longs(g, addr, n):
    out = g.cmd(f'x/{n}xw {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return vals[:n]


def sample(g):
    fields, = longs(g, FIELDS, 1)
    buf, = longs(g, BUFFER, 1)
    clock, = longs(g, CLOCK, 1)
    pos, = longs(g, POS, 1)
    step = longs(g, STEP, 1)[0] >> 16   # the word at $DC60: the long's high half
    return fields, buf, clock, pos, step


def meter(server, g, rest):
    """meter <fields>: step one field at a time (read-only) and report frames (buffer toggles),
    race-clock, distance and step rates. At most one swap per field (the race loop waits for a
    field change after each), so a parity sample per field counts every frame."""
    n = int(rest.split()[0]) if rest.split() else 250
    g.stop()
    g.cmd('monitor fields 1')
    f0, b0, c0, p0, _ = sample(g)
    frames, last, steps, gaps, since = 0, b0, [], [], 0
    for _ in range(n):
        g.cmd('monitor fields 1')
        f, b, c, p, s = sample(g)
        since += 1
        steps.append(s)
        if b != last:
            frames += 1
            gaps.append(since)
            since = 0
            last = b
    g.cont()
    fields = f - f0
    hist = {k: gaps.count(k) for k in sorted(set(gaps))}
    return (f'fields {fields} frames {frames} fps {50.0 * frames / max(fields, 1):.2f} '
            f'fields/frame {hist}\n'
            f'clock +{c - c0} ({(c - c0) / max(fields, 1):.2f}/field) '
            f'distance +{p - p0} ({(p - p0) / max(fields, 1):.1f}/field, '
            f'{(p - p0) / max(frames, 1):.1f}/frame) mean step {sum(steps) / len(steps):.1f}')


def race_log(server, g, rest):
    """racelog <fields> <file>: wait for a race start (the race clock leaving 0; polled every
    field for at most 6000), then step one field at a time for <fields> fields and write one
    line per field: field counter, frame number (buffer toggles since the start), race clock,
    distance. Field 0 is the first with the clock running: the green light on every machine."""
    args = rest.split()
    n, path = int(args[0]), args[1]
    g.stop()
    _, _, prev, _, _ = sample(g)
    for _ in range(6000):
        g.cmd('monitor fields 1')
        _, b, c, _, _ = sample(g)
        if prev == 0 and 0 < c <= 4:
            break
        prev = c
    else:
        g.cont()
        return 'no race start within 6000 fields'
    frames, last, rows = 0, b, []
    for _ in range(n):
        g.cmd('monitor fields 1')
        f, b, c, p, s = sample(g)
        if b != last:
            frames, last = frames + 1, b
        rows.append(f'{f} {frames} {c} {p}')
    g.cont()
    with open(path, 'w') as out:
        out.write('\n'.join(rows) + '\n')
    return f'{n} fields, {frames} frames, clock {rows[0].split()[2]}..{c}'


server = game_server('vroom', commands={'decrunch': decrunch, 'meter': meter,
                                        'racelog': race_log})
if __name__ == '__main__':
    server.main(sys.argv[1:])
