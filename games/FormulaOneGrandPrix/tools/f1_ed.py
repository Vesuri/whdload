#!/usr/bin/env python3
"""Drive F1GP-Ed 3.44 under Workbench in FS-UAE (amiga/ed.sh) for F1's write map.

  python3 tools/f1_ed.py serve          boot amiga/ed.sh DEBUG=1, attach gdb, run; listen
  python3 tools/f1_ed.py <command...>   send one command to the running server

Commands are the shared server's (shot <png>, fields via gdb, quit, ...) and:
  click X Y          home the pointer, move it to screenshot pixel X,Y and click the left button
  menu X Y [X Y]...  home the pointer, hold the right button at X,Y, move through the given
                     points (menu, item, sub-item) and release at the last
  hold X Y [X Y]...  the same without releasing the button (to inspect a menu)
  move X Y           home the pointer and move it to X,Y
  key RAW [FIELDS]   press a hexadecimal raw key for FIELDS (default 5), then release
  run FIELDS         let FIELDS PAL fields pass

The pointer is homed to the screen's top-left clamp (HOME, screenshot pixels) and moved in
steps of at most STEP counts, below Intuition's mouse acceleration threshold.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server
from amigaxdev.input import Input

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('FSUAE', os.environ.get('FSUAE_ARM')
                      or os.path.expanduser('~/.local/share/amiga/fs-uae-arm/fs-uae'))
HOME = tuple(int(v) for v in os.environ.get('F1ED_HOME', '74,54').split(','))
SCALE = tuple(float(v) for v in os.environ.get('F1ED_SCALE', '1,1').split(','))
STEP = int(os.environ.get('F1ED_STEP', '2'))


def home(c):
    for _ in range(12):
        c.mouse(-64, -64, fields=1)


def travel(c, frm, to):
    dx = round((to[0] - frm[0]) / SCALE[0])
    dy = round((to[1] - frm[1]) / SCALE[1])
    while dx or dy:
        sx, sy = max(-STEP, min(STEP, dx)), max(-STEP, min(STEP, dy))
        c.mouse(sx, sy, fields=1)
        dx, dy = dx - sx, dy - sy
    c.fields(3)


def points(rest):
    v = [int(n) for n in rest.split()]
    if not v or len(v) % 2:
        raise ValueError('expected X Y pairs')
    return list(zip(v[::2], v[1::2]))


def click(server, g, rest):
    (p,) = points(rest)
    g.stop()
    with Input(g) as c:
        home(c); travel(c, HOME, p)
        c.button('JOY1_FIRE_BUTTON', True); c.fields(3)
        c.button('JOY1_FIRE_BUTTON', False); c.fields(3)
    return 'clicked; CPU stopped'


def menu(server, g, rest, release=True):
    ps = points(rest)
    g.stop()
    c = Input(g)
    home(c); travel(c, HOME, ps[0])
    c.button('JOY1_2ND_BUTTON', True); c.fields(5)
    for a, b in zip(ps, ps[1:]):
        travel(c, a, b); c.fields(5)
    if release:
        c.button('JOY1_2ND_BUTTON', False); c.fields(5)
    return 'menu selected; CPU stopped'


def move(server, g, rest):
    (p,) = points(rest)
    g.stop()
    with Input(g) as c:
        home(c); travel(c, HOME, p)
    return 'moved; CPU stopped'


def key(server, g, rest):
    a = rest.split()
    g.stop()
    with Input(g) as c:
        c.key(int(a[0], 16), True); c.fields(int(a[1]) if len(a) > 1 else 5)
        c.key(int(a[0], 16), False); c.fields(3)
    return 'released; CPU stopped'


def run(server, g, rest):
    g.stop()
    with Input(g) as c:
        c.fields(int(rest))
    return 'ran; CPU stopped'


server = Server('f1ed', root=ROOT, run_script='amiga/ed.sh', profile_window=False,
                commands={'click': click, 'menu': menu, 'hold': lambda s_, g, r: menu(s_, g, r, False), 'move': move, 'key': key, 'run': run})

if __name__ == '__main__':
    server.main(sys.argv[1:])
