"""Zany Golf gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/zanygolf.py serve          boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/zanygolf.py wait 20        then shot, gdb, profile, quit, ...
    python3 tools/zanygolf.py frames N [DX DY K]
                                             run N fields one at a time and count the frames
                                             shown: flips of the copper list's plane pointer
                                             (program offset $14a8 flips it); no breakpoint,
                                             so it works on every CPU, MMU cores included.
                                             With DX DY: move the mouse by DX, DY every field,
                                             reversing direction every K fields (default 30)

Stop the CPU first (`stop`, or tools/route.py's routes do): the server resumes a CPU that was
running before a command.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

PLANE4 = 0x12326     # the low word of BPL4PT in the copper list; bit 15 picks the buffer
COUNTER = 0x1145c    # the game's field counter, low byte first


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


def server_ntsc():
    import os
    return os.environ.get('NTSC', '1') == '1'


server = game_server('zanygolf', commands={'frames': frames})
if __name__ == '__main__':
    server.main(sys.argv[1:])
