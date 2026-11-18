#!/usr/bin/env python3
"""Plays archipelago 1 through a running server, aiming the crosshair from the game's state.

    python3 tools/play.py stones       collapse every stone (the six-frame effect, $CD1C)
    python3 tools/play.py obelisk      then destroy the Obelisk (the ramps, $C5D0)
    python3 tools/play.py goto X Y     click map cell X, Y (hex) from wherever it can

tools/route.py runs them as the steps 'stones' and 'obelisk' after 'start'. Offsets below
are SPS 627's, then SPS 628's (VARIANT=ArchipelagosNTSC, as for tools/route.py). Needs
cursor mode (the game starts in it) and archipelago 1, where every stone is on the
Obelisk's island.

The crosshair's cell is the game's own projection (`$11F72`): the renderer leaves a row
table at offset `$12FA6` for the current heading, a start and a step (8.8 map positions)
for each of the pointer's 51 rows, and the cell is the start plus the step times the
pointer's X / 256. So every cell the crosshair can reach is known, and a cell is aimed at
by moving the mouse until the pointer is on it, then checked against the table again.
A cell out of reach is approached: turn towards it (the pointer at the screen's edge turns
the view a degree a frame, until it leaves the edge), then move to the reachable land cell
nearest to it, no nearer than 5 cells (the crosshair reaches about 3 to 9 cells ahead). The
map wraps.
"""
import math
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import archipelagos  # noqa: E402

US = os.environ.get('VARIANT') == 'ArchipelagosNTSC'


def body():
    import route
    return route.body()


def v(o627, o628):
    return o628 if US else o627


PTR_Y, PTR_X = v(0xe5e4, 0xe638), v(0xe5e6, 0xe63a)   # the pointer (words; high byte)
HEADING = v(0x12880, 0x12c24)          # 0-719, half degrees
POS = v(0x129be, 0x12d62)              # x, y (words, 8.8)
ROWS = v(0x12fa6, 0x1334a)             # the crosshair's row table (51 x 4 words)
STONES = v(0x12b98, 0x12f3c)           # the stones' cells (words; cleared when collapsed)
NSTONES = v(0x12e58, 0x131fc)
LEFT = v(0x129dc, 0x12d80)             # stones not yet collapsed
OBELISK = v(0x129e6, 0x12d8a)          # the Obelisk's cell
FIELDS, BACK = v(0x12862, 0x12c06), v(0x1286a, 0x12c0e)
STONE = v(0x12b96, 0x12f3a)            # the six-frame effect's count
RAMP1, RAMP2 = v(0xcf1c, 0xcf48), v(0xcf1e, 0xcf4a)
MAP = 0x78000                          # the map's middle (an absolute address)
NEAR = 5                               # cells: no nearer than this to a target


def req(line):
    out = archipelagos.server.request(line)
    if 'rror' in out:
        sys.exit(f'{line[:80]}: {out}')
    return out


def batch(*cmds):
    return req('batch ' + ' ;; '.join(cmds))


def peek(addr, n):
    vals = []
    for line in batch(f'x/{n}xb {addr:#x}').splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return bytes(vals[:n])


def var(off, n=2, signed=True):
    return int.from_bytes(peek(body() + off, n), 'big', signed=signed)


# record(): from then on every field's clocks go to RECORD, one tuple a field (CLOCKS).
CLOCKS = [('fields', FIELDS, 'unsigned int'), ('back', BACK, 'unsigned int'),
          ('stone', STONE, 'short'), ('ramp1', RAMP1, 'unsigned short'),
          ('ramp2', RAMP2, 'unsigned short'), ('left', LEFT, 'short'),
          ('x', POS, 'unsigned short'), ('y', POS + 2, 'unsigned short')]
RECORD = None


def _print():
    return ('printf "@ ' + ' '.join(['%u'] * len(CLOCKS)) + '\\n", '
            + ', '.join(f'*({t} *){body() + a:#x}' for _, a, t in CLOCKS))


def record():
    global RECORD
    RECORD = []


def fields(n):
    if RECORD is None:
        batch(f'monitor fields {n}')
    else:
        _fields(n)


def _fields(n, pre=()):
    out = batch(*pre, *(['monitor fields 1', _print()] * n))
    RECORD.extend(tuple(int(v) for v in l[2:].split()) for l in out.splitlines()
                  if l.startswith('@ '))


def mouse(dx, dy, n=1):
    if RECORD is None:
        batch(*[f'monitor mouse {dx} {dy} ;; monitor fields 1'] * n)
    else:
        for _ in range(n):
            _fields(1, [f'monitor mouse {dx} {dy}'])


def click():
    if RECORD is None:
        batch('monitor input JOY1_FIRE_BUTTON 1', 'monitor fields 4',
              'monitor input JOY1_FIRE_BUTTON 0')
    else:
        _fields(4, ['monitor input JOY1_FIRE_BUTTON 1'])
        batch('monitor input JOY1_FIRE_BUTTON 0')


def wr(v):
    """A map distance across the wrap."""
    return (v + 128) % 256 - 128


def pos():
    b = peek(body() + POS, 4)
    return b[0] + b[1] / 256, b[2] + b[3] / 256


def ptr():
    return var(PTR_X, signed=False) >> 8, var(PTR_Y, signed=False) >> 8


def rows():
    t = peek(body() + ROWS, 51 * 8)
    return [struct.unpack_from('>4h', t, r * 8) for r in range(51)]


def target(t, px, py):
    """The cell under the pointer, as $11F72 computes it."""
    x0, y0, dx, dy = t[50 - py]
    return ((x0 + (dx * px >> 8)) & 0xffff) >> 8, ((y0 + (dy * px >> 8)) & 0xffff) >> 8


def reach(t):
    m = {}
    for py in range(51):
        for px in range(256):
            m.setdefault(target(t, px, py), (px, py))
    return m


def cell(c):
    return peek(MAP + struct.unpack('>h', bytes([c[1], c[0]]))[0], 1)[0]


def land(c):
    v = cell(c)
    return not v & 0x80 and v & 7 in (6, 7)   # what a move accepts ($1190A)


def dist(a, b):
    return math.hypot(wr(a[0] - b[0]), wr(a[1] - b[1]))


def off(c):
    """Degrees from the view's centre to cell c (positive: to the right)."""
    p, (fx, fy) = pos(), target(rows(), 128, 0)
    a = math.atan2(wr(fy + .5 - p[1]), wr(fx + .5 - p[0]))
    b = math.atan2(wr(c[1] + .5 - p[1]), wr(c[0] + .5 - p[0]))
    return math.degrees((b - a + math.pi) % (2 * math.pi) - math.pi)


def point(px, py):
    for _ in range(60):
        x, y = ptr()
        if (x, y) == (px, py):
            return True
        mouse(max(-8, min(8, (px - x) * 2)), max(-8, min(8, (py - y) * 2)))
    return False


def turn(deg):
    x, y = ptr()
    point(255 if deg > 0 else 0, y)
    mouse(8 if deg > 0 else -8, 0, int(abs(deg)))
    point(128, y)                               # off the edge: the turn stops
    fields(20)                                  # a frame with the new heading's table


def aim(c):
    for _ in range(4):
        m = reach(rows())
        if c not in m:
            return False
        point(*m[c])
        fields(20)
        if target(rows(), *ptr()) == c:
            return True
    return False


def goto(c, log=print):
    """Click cell c, approaching it first; False if it cannot."""
    for _ in range(16):
        d = off(c)
        p = pos()
        log(f'at {p[0]:.1f},{p[1]:.1f} heading {var(HEADING)}: {c[0]:02x},{c[1]:02x} '
            f'{dist(p, c):.1f} cells, {d:.0f} degrees off')
        if abs(d) > 15:
            turn(d)
            continue
        if c in reach(rows()) and aim(c):
            click()
            return True
        steps = [s for s in reach(rows())
                 if NEAR <= dist(s, c) < dist(p, c) - 1.5 and land(s)]
        if not steps:
            log('nothing reachable nearer')
            return False
        s = min(steps, key=lambda s: dist(s, c))
        if aim(s):
            click()
            fields(150)                         # a move takes 65 fields on an A500
    return False


def stones(log=print):
    n = var(NSTONES)
    for i in range(n):
        s = var(STONES + 2 * i, signed=False)
        if not s:
            continue
        left = var(LEFT)
        if not goto((s & 0xff, s >> 8), log):
            sys.exit(f'stone {s:04x}: not reached')
        fields(100)
        if var(LEFT) != left - 1:
            sys.exit(f'stone {s:04x}: not collapsed')
        log(f'stone {s:04x} collapsed, {left - 1} left')


def obelisk(log=print):
    o = var(OBELISK, signed=False)
    if var(LEFT):
        sys.exit('stones left')
    if not goto((o & 0xff, o >> 8), log):
        sys.exit(f'Obelisk {o:04x}: not reached')
    log(f'Obelisk {o:04x} clicked')


def main(args):
    if args == ['stones']:
        stones()
    elif args == ['obelisk']:
        obelisk()
    elif len(args) == 3 and args[0] == 'goto':
        sys.exit(0 if goto((int(args[1], 16), int(args[2], 16))) else 1)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
