"""Archipelagos gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/archipelagos.py serve      boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/archipelagos.py wait 20    then shot, gdb, profile, quit, ...
    python3 tools/archipelagos.py frames N [DX]
                                             run N fields one at a time (moving the mouse DX
                                             counts right before each, default 0) and count
                                             the frames shown: flips of the back buffer
                                             pointer $14886, which the swap (program offset
                                             $12210) exchanges. A frame takes at least two
                                             fields, so reading it each field misses none.
                                             No breakpoint and no trace, so it works on every
                                             CPU, MMU cores included. Also reports the world
                                             ticks (reloads of the countdown $149d2) and the
                                             heading turned.

Stop the CPU first (`stop`, or tools/route.py's routes do): the server resumes a CPU that was
running before a command.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

BACK = 0x14886       # the buffer being drawn: $5c780 or $663c0
TICK = 0x149d2       # the world tick countdown (the VBL decrements it; a tick reloads it)
HEADING = 0x1489c    # 0..719, half degrees


def _peek(g, addr, n, signed=False):
    out = g.cmd(f'x/{n}xb {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return int.from_bytes(bytes(vals[:n]), 'big', signed=signed)


def frames(server, g, rest):
    w = rest.split()
    n = int(w[0]) if w else 250
    dx = int(w[1]) if len(w) > 1 else 0
    g.stop()
    back, tick, head = _peek(g, BACK, 4), _peek(g, TICK, 2, True), _peek(g, HEADING, 2)
    flips, ticks, turned, gaps, last = 0, 0, 0, [], None
    for i in range(n):
        if dx:
            g.cmd(f'monitor mouse {dx} 0')
        g.cmd('monitor fields 1')
        b, t, h = _peek(g, BACK, 4), _peek(g, TICK, 2, True), _peek(g, HEADING, 2)
        if b != back:
            flips += 1
            if last is not None:
                gaps.append(i - last)
            last = i
        if t > tick:                     # reloaded (5) from a lower or negative value
            ticks += 1
        turned += (h - head) % 720
        back, tick, head = b, t, h
    fps = flips * 50 / n
    span = (f', fields a frame {min(gaps)}-{max(gaps)} mean {sum(gaps) / len(gaps):.2f}'
            if gaps else '')
    return (f'{n} fields: {flips} frames, {fps:.2f} fps{span}; {ticks} world ticks; '
            f'heading turned {turned / 2:.0f} degrees\n')


server = game_server('archipelagos', commands={'frames': frames})

if __name__ == '__main__':
    server.main(sys.argv[1:])
