"""Zany Golf gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/zanygolf.py serve          boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/zanygolf.py wait 20        then shot, gdb, profile, quit, ...
    python3 tools/zanygolf.py frames N [DX DY K]
                                             run N fields one at a time and count the frames
                                             shown: flips of the copper list's plane pointer
                                             (program offset $14ac flips it); no breakpoint,
                                             so it works on every CPU, MMU cores included.
                                             With DX DY: move the mouse by DX, DY every field,
                                             reversing direction every K fields (default 30)
    python3 tools/zanygolf.py track N FILE   run N fields one at a time and write a line a
                                             field to FILE: the game's field counter, 1 if a
                                             frame was shown in it, the game clock, the ball's
                                             x, y and its two velocity components
    python3 tools/zanygolf.py frametrack N FILE
                                             run to the renderer's flip N times (a breakpoint at
                                             program offset $14ac; not on MMU cores) and write a
                                             line a frame: the field counter, the clock and the
                                             object block $5c7a-$5d29 in hex

Stop the CPU first (`stop`, or tools/route.py's routes do): the server resumes a CPU that was
running before a command.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

PLANE4 = 0x12326     # the low word of BPL4PT in the copper list; bit 15 picks the buffer
SWAP = 0x114ac       # the renderer flips PLANE4 and the other plane pointers here (the
                     # first instruction after the slave's jsr FrameCap at $114a4)
COUNTER = 0x1145c    # the game's field counter, low byte first
CLOCK = 0x15de6      # the game clock in fields: the elapsed-fields sum $5de4 less the epoch $6424
BALL = 0x15c7a       # the ball (object 0 of four): x, then y at +8 (pixels on the course
                     # map), the velocity at +$10 and +$18 (signed, along the course's diagonal
                     # axes, not x and y), 16-bit little-endian


def _peek(g, addr, n):
    out = g.cmd(f'x/{n}xb {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return vals[:n]


def frames(server, g, rest):
    """Frames shown in N fields: plane-pointer flips seen at each field's end. A frame takes
    more than a field here, so none is missed; fewer than a field a frame would be undercounted
    (the reply's fields-per-frame minimum says so)."""
    w = rest.split()
    n = int(w[0]) if w else 120
    dx, dy = (int(w[1]), int(w[2])) if len(w) > 2 else (0, 0)
    k = int(w[3]) if len(w) > 3 else 30
    g.stop()
    hi = lambda: _peek(g, PLANE4, 1)[0] & 0x80
    c0 = _peek(g, COUNTER, 2)
    last, flips, stamps = hi(), 0, []
    for i in range(n):
        if dx or dy:
            sign = -1 if (i // k) % 2 else 1
            g.cmd(f'monitor mouse {sign * dx} {sign * dy}')
        g.cmd('monitor fields 1')
        now = hi()
        if now != last:
            flips += 1
            stamps.append(i + 1)
        last = now
    c1 = _peek(g, COUNTER, 2)
    counted = ((c1[0] | c1[1] << 8) - (c0[0] | c0[1] << 8)) & 0xffff
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    hz = 60 if server_ntsc() else 50
    s = (f'fields {n} (game counter {counted})  frames {flips}  '
         f'= {hz * flips / n:.2f} frames a second at {hz} Hz')
    if gaps:
        s += f'  fields between flips: mean {sum(gaps) / len(gaps):.2f} min {min(gaps)} max {max(gaps)}'
    return s


def track(server, g, rest):
    """One line a field: counter shown clock x y v1 v2 (the state at the field's end)."""
    w = rest.split()
    n, path = int(w[0]), w[1]
    g.stop()
    le = lambda b, i: b[i] | b[i + 1] << 8
    sx = lambda v: v - 0x10000 if v & 0x8000 else v
    hi = lambda: _peek(g, PLANE4, 1)[0] & 0x80
    last = hi()
    lines = ['counter shown clock x y v1 v2']
    for _ in range(n):
        g.cmd('monitor fields 1')
        now = hi()
        c, k, b = _peek(g, COUNTER, 2), _peek(g, CLOCK, 2), _peek(g, BALL, 26)
        lines.append(f'{le(c, 0)} {int(now != last)} {le(k, 0)} {le(b, 0)} {le(b, 8)} '
                     f'{sx(le(b, 16))} {sx(le(b, 24))}')
        last = now
    Path(path).write_text('\n'.join(lines) + '\n')
    return f'{n} fields to {path}'


def frametrack(server, g, rest):
    """One line a frame at the flip: counter clock and the object block in hex."""
    w = rest.split()
    n, path = int(w[0]), w[1]
    g.stop()
    g.cmd(f'break *{SWAP:#x}')
    lines = ['counter clock objects($5c7a-$5d29)']
    try:
        for _ in range(n):
            g.cmd('continue', timeout=600)
            c, k = _peek(g, COUNTER, 2), _peek(g, CLOCK, 2)
            lines.append(f'{c[0] | c[1] << 8} {k[0] | k[1] << 8} ' + bytes(_peek(g, BALL, 0xb0)).hex())
    finally:
        g.cmd('delete')
    Path(path).write_text('\n'.join(lines) + '\n')
    return f'{n} frames to {path}'


def server_ntsc():
    import os
    return os.environ.get('NTSC', '1') == '1'


server = game_server('zanygolf', commands={'frames': frames, 'track': track, 'frametrack': frametrack})
if __name__ == '__main__':
    server.main(sys.argv[1:])
