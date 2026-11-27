#!/usr/bin/env python3
"""Stunt Car Racer gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/scr.py serve            boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/scr.py fields N         run N whole fields and stay stopped
    python3 tools/scr.py keys K[:N] ...   press each raw key (hex) for 8 fields, then run N
                                          fields (default 25); K+ holds it, K- releases it
    python3 tools/scr.py peek ADDR [N]    N bytes at ADDR (hex), the CPU stopped
    python3 tools/scr.py wait 20 | shot x.png | profile N x.bin | quit | ...

The menus take the number keys (raw $01-$09) and RETURN ($44); in a race RETURN accelerates
with boost, S and D ($21, $22) steer.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402


def peek_bytes(g, addr, n):
    out = g.cmd(f'x/{n}xb {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return bytes(vals[:n])


def fields(server, g, rest):
    n = int(rest.split()[0]) if rest.strip() else 1
    g.stop()
    return g.cmd(f'monitor fields {n}', timeout=3600)


def keys(server, g, rest):
    g.stop()
    for k in rest.split():
        k, _, n = k.partition(':')
        if k.endswith('+'):
            g.cmd(f'monitor key {k[:-1]} 1')
        elif k.endswith('-'):
            g.cmd(f'monitor key {k[:-1]} 0')
        else:
            g.cmd(f'monitor key {k} 1')
            g.cmd('monitor fields 8', timeout=600)
            g.cmd(f'monitor key {k} 0')
        g.cmd(f'monitor fields {int(n or 25)}', timeout=3600)
    return 'ok\n'


def peek(server, g, rest):
    w = rest.split()
    g.stop()
    return peek_bytes(g, int(w[0], 16), int(w[1]) if len(w) > 1 else 4).hex() + '\n'


server = game_server('scr', commands={'fields': fields, 'keys': keys, 'peek': peek})

if __name__ == '__main__':
    server.main(sys.argv[1:])
