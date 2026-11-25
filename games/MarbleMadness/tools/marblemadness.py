"""Marble Madness game server: the shared built-ins plus field-exact input steps.

    python3 tools/marblemadness.py serve      boot (common/run.sh options in the environment)
    python3 tools/marblemadness.py menu       from the boot to the options menu, then Mouse Port
                                              and Mouse selected, pointer on GO!; stays stopped
    python3 tools/marblemadness.py go         click GO! and run until the practice race starts
    python3 tools/marblemadness.py step DX DY FIELDS [N]
                                              N times: add DX,DY to the mouse, run FIELDS fields
    python3 tools/marblemadness.py chain FIELDS DX DY BIN
                                              profile FIELDS fields in one-field chunks,
                                              moving the mouse DX,DY before each (BIN.NNN)
    python3 tools/marblemadness.py click      one menu click (a 6-field press, 40 fields of release)
    python3 tools/marblemadness.py watch ADDR FIELDS
                                              run FIELDS fields one at a time and list the
                                              fields where the word at ADDR changes
    python3 tools/marblemadness.py dump OUT [START END]
                                              memory START..END (default 0..$200000, chip RAM
                                              of every setup) into OUT, for tools/mmtrace.py segmap;
                                              on fast-memory setups dump $940000..$A00000 too

Every command stops the CPU first and leaves it stopped, so fields are counted exactly; the
built-in `cont` resumes. The menu is a gray screen whose pointer is the ball; one mouse count
moves it two screen pixels. A click is a 6-field press and 40 fields of release (a longer
press repeats). Positions are from the boot's pointer position, which the menu starts with.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402
from amigaxdev.gdbserve import profile  # noqa: E402

BUTTON = 'JOY1_FIRE_BUTTON'     # port-0 mouse left button


def mon(g, text):
    out = g.cmd(f'monitor {text}', timeout=600)
    if 'error' in out.lower():
        raise RuntimeError(f'monitor {text}: {out}')
    return out


def fields(g, n):
    while n > 0:
        k = min(n, 6000)
        mon(g, f'fields {k}')
        n -= k


def mouse(g, dx, dy):
    # The counters are 8 bits: steps of at most 64 with a field between them.
    while dx or dy:
        sx = max(-64, min(64, dx))
        sy = max(-64, min(64, dy))
        mon(g, f'mouse {sx} {sy}')
        fields(g, 2)
        dx -= sx
        dy -= sy


def click(g):
    mon(g, f'input {BUTTON} 1')
    fields(g, 6)
    mon(g, f'input {BUTTON} 0')
    fields(g, 40)


def cmd_menu(server, g, rest):
    g.stop()
    fields(g, int(rest or 1000))            # boot, intro, menu
    mouse(g, 0, -81)                        # Red Player
    fields(g, 5)
    click(g)                                # Joy Port -> Mouse Port
    mouse(g, 0, 16)                         # Input Device
    fields(g, 5)
    for _ in range(3):                      # Joy Stick -> Trackball 1 -> 2 -> Mouse
        click(g)
    mouse(g, -31, 56)                       # GO!
    fields(g, 20)
    return 'menu ready'


def cmd_go(server, g, rest):
    g.stop()
    click(g)
    fields(g, int(rest or 1500))
    return 'ok'


def cmd_step(server, g, rest):
    g.stop()
    a = rest.split()
    dx, dy, n = int(a[0]), int(a[1]), int(a[2])
    for _ in range(int(a[3]) if len(a) > 3 else 1):
        mouse(g, dx, dy) if (dx or dy) else None
        fields(g, n)
    return 'ok'


def cmd_chain(server, g, rest):
    g.stop()
    n, dx, dy, target = rest.split(None, 3)
    for i in range(int(n)):
        if int(dx) or int(dy):
            mon(g, f'mouse {dx} {dy}')
        profile(g, 1, f'{target}.{i:03d}')
    return 'ok'


def cmd_click(server, g, rest):
    g.stop()
    click(g)
    return 'ok'


def cmd_watch(server, g, rest):
    g.stop()
    addr, n = rest.split()
    out, last = [], None
    for i in range(int(n)):
        v = g.cmd(f'x/hx {addr}').split()[-1]
        if v != last:
            out.append(f'{i}:{v}')
            last = v
        fields(g, 1)
    return ' '.join(out)


def cmd_dump(server, g, rest):
    g.stop()
    a = rest.split()
    start, end = (a[1], a[2]) if len(a) > 2 else ('0', '0x200000')
    g.cmd(f'dump binary memory {a[0]} {start} {end}', timeout=600)
    return f'{a[0]} {start}..{end}'


server = game_server('game', commands={'menu': cmd_menu, 'go': cmd_go, 'step': cmd_step,
                                       'chain': cmd_chain, 'click': cmd_click, 'watch': cmd_watch,
                                       'dump': cmd_dump})
if __name__ == '__main__':
    server.main(sys.argv[1:])
