"""Links' gdb-stub server: common/tools/game_server.py plus mouse commands.

    python3 tools/links.py serve           boot (common/run.sh DEBUG=1) and listen
    python3 tools/links.py move DX DY      move the mouse by DX, DY counts (in steps of 20)
    python3 tools/links.py click [N]       press the left button for N fields (default 3)
    python3 tools/links.py play [SCALE]    from the title menu to the first hole: START, OK,
                                           DEFAULT, OK, OK (the moves are the menu's positions;
                                           SCALE multiplies the waits)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

STEP = 20


def _fields(g, n):
    g.cmd(f'monitor fields {n}', timeout=120)


def _move(g, dx, dy):
    while dx or dy:
        sx = max(-STEP, min(STEP, dx))
        sy = max(-STEP, min(STEP, dy))
        g.cmd(f'monitor mouse {sx} {sy}')
        _fields(g, 1)
        dx -= sx
        dy -= sy


def _click(g, n=3):
    g.cmd('monitor input JOY1_FIRE_BUTTON 1')
    _fields(g, n)
    g.cmd('monitor input JOY1_FIRE_BUTTON 0')
    _fields(g, n)


def move(server, g, rest):
    g.stop()
    dx, dy = (int(v) for v in rest.split())
    _move(g, dx, dy)
    g.cont()
    return 'ok'


def click(server, g, rest):
    g.stop()
    _click(g, int(rest or 3))
    g.cont()
    return 'ok'


# From the title menu (the pointer where the game puts it): START, the course list's OK,
# DEFAULT in the player file, OK, then the ready screen's OK. (DX, DY, fields to wait after
# the click.)
ROUTE = [(-50, -34, 100), (139, 89, 100), (3, -96, 30), (-3, 51, 100), (-140, 64, 0)]


def play(server, g, rest):
    """Run the route; the title menu must be up (CUSTOM1=1 skips the intro). The optional
    argument multiplies the waits (a 68000 loads each screen more slowly)."""
    scale = float(rest or 1)
    g.stop()
    for dx, dy, wait in ROUTE:
        _move(g, dx, dy)
        _click(g, 6)
        if wait:
            _fields(g, int(wait * scale))
    g.cont()
    return 'ok'


server = game_server('links', commands={'move': move, 'click': click, 'play': play})

if __name__ == '__main__':
    server.main(sys.argv[1:])
