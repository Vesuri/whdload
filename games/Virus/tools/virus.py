"""Virus gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/virus.py serve           boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/virus.py fields N        run N whole fields and stay stopped at a vsync
    python3 tools/virus.py peek ADDR N     N bytes at ADDR (hex), the CPU stopped
    python3 tools/virus.py wait 20 | shot x.png | profile N x.bin | quit | ...

Stop the CPU first (`stop`): the server resumes a CPU that was running before a command.
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


def peek(server, g, rest):
    w = rest.split()
    g.stop()
    return peek_bytes(g, int(w[0], 16), int(w[1]) if len(w) > 1 else 4).hex() + '\n'


server = game_server('virus', commands={'fields': fields, 'peek': peek})

if __name__ == '__main__':
    server.main(sys.argv[1:])
