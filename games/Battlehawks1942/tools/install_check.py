#!/usr/bin/env python3
"""Drive the release installer in FS-UAE (tools/install_run.sh boots it) through the gdb stub.

  python3 tools/install_check.py serve            boot, attach gdb, listen
  python3 tools/install_check.py <command...>     one command to the running server

Commands, besides the shared server's (stop, cont, gdb, shot, wait, quit):
  pointer            Intuition's pointer position (screen pixels)
  click X Y          move the pointer to X, Y and click the left button
  key RAW            press and release raw key RAW (hex)
  disk N             put tmp/game/Battlehawks1942/Disk.N in DF0 (rewrites df0.adf in place)
"""
import os, shutil, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server  # noqa: E402
from amigaxdev.input import Input  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUN = 'tmp/run/install/.run'


def word(g, adr):
    out = g.cmd(f'x/1hx {adr:#x}')
    return int(out.split(':')[1].split()[0], 16)


def long(g, adr):
    out = g.cmd(f'x/1wx {adr:#x}')
    return int(out.split(':')[1].split()[0], 16)


def cstr(g, adr):
    out = g.cmd(f'x/s {adr:#x}')
    return out.split(':', 1)[1].strip().strip('"')


def intuition(g):
    node = long(g, long(g, 4) + 378)              # ExecBase->LibList.lh_Head
    while long(g, node):
        if cstr(g, long(g, node + 10)) == 'intuition.library':
            return node
        node = long(g, node)
    raise RuntimeError('no intuition.library')


def pointer(g):
    ib = intuition(g)
    y, x = word(g, ib + 68), word(g, ib + 70)     # ib_MouseY, ib_MouseX (lores pixels)
    return (x - 0x10000 if x & 0x8000 else x), (y - 0x10000 if y & 0x8000 else y)


def stopped(fn):
    def run(server, g, rest):
        was = g.running
        g.stop()
        try:
            return fn(server, g, rest)
        finally:
            if was:
                g.cont()
    return run


@stopped
def c_pointer(server, g, rest):
    return '%d %d' % pointer(g)


@stopped
def c_click(server, g, rest):
    tx, ty = (int(v) for v in rest.split())
    with Input(g) as c:
        for _ in range(60):
            x, y = pointer(g)
            if (x, y) == (tx, ty):
                break
            # Intuition's pointer moves one lores pixel per two mouse counts, more when fast.
            c.mouse(max(-32, min(32, tx - x)), max(-32, min(32, ty - y)), fields=2)
        else:
            raise RuntimeError(f'pointer stuck at {pointer(g)}, wanted {tx} {ty}')
        c.button('JOY1_FIRE_BUTTON', True)
        c.fields(5)
        c.button('JOY1_FIRE_BUTTON', False)
        c.fields(25)
    return 'clicked %d %d' % (tx, ty)


@stopped
def c_key(server, g, rest):
    raw = int(rest, 16)
    with Input(g) as c:
        c.key(raw, True)
        c.fields(5)
        c.key(raw, False)
        c.fields(25)
    return 'key %02x' % raw


def c_disk(server, g, rest):
    src = ROOT / f'tmp/game/Battlehawks1942/Disk.{int(rest)}'
    dst = ROOT / RUN / 'df0.adf'
    with open(src, 'rb') as s, open(dst, 'r+b') as d:   # in place: FS-UAE keeps it open
        shutil.copyfileobj(s, d)
    return f'df0.adf is now {src.name}'


server = Server('install', root=str(ROOT), run_script='tools/install_run.sh', run_dir=RUN,
                commands={'pointer': c_pointer, 'click': c_click, 'key': c_key, 'disk': c_disk})

if __name__ == '__main__':
    server.main(sys.argv[1:])
