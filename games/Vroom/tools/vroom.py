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


server = game_server('vroom', commands={'decrunch': decrunch})
if __name__ == '__main__':
    server.main(sys.argv[1:])
