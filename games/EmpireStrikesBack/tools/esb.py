"""Empire Strikes Back gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/esb.py serve               boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/esb.py wait 20             then shot, quit, ...
    python3 tools/esb.py fire N              hold the trigger (left mouse button) N fields
    python3 tools/esb.py mouse DX DY [N]     move the mouse by DX, DY a field, N fields
    python3 tools/esb.py cover N FILE        profile N fields; add every PC executed in the
                                             game image ($500-$5e500) to FILE (one hex
                                             address a line, kept sorted)
    python3 tools/esb.py mem ADDR LEN FILE   LEN bytes at ADDR (gdb syntax) to FILE
    python3 tools/esb.py hits ADDR N EXPR... stop N times at ADDR (hex) and print each EXPR

Addresses are the game's runtime addresses (the image is loaded at $500).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402
from amigaxdev.gdbserve import profile  # noqa: E402


def fire(server, g, rest):
    g.stop()
    g.cmd('monitor input JOY1_FIRE_BUTTON 1')
    g.cmd(f'monitor fields {int(rest or 5)}')
    g.cmd('monitor input JOY1_FIRE_BUTTON 0')
    g.cont()
    return 'ok'


def mouse(server, g, rest):
    dx, dy, *n = rest.split()
    g.stop()
    for _ in range(int(n[0]) if n else 1):
        g.cmd(f'monitor mouse {int(dx)} {int(dy)}')
        g.cmd('monitor fields 1')
    g.cont()
    return 'ok'


def cover(server, g, rest):
    n, path = rest.split()
    path = Path(os.path.abspath(path))
    target = path.with_suffix('.trace')
    g.stop()
    try:
        _, trace = profile(g, int(n), target)
    finally:
        g.cont()
    pcs = set()
    if path.exists():
        pcs = {int(x, 16) for x in path.read_text().split()}
    before = len(pcs)
    for f in trace.fields:
        for pc, _, _ in trace.instructions(f):
            if pc is not None and 0x500 <= pc < 0x5e500:
                pcs.add(pc)
    path.write_text(''.join(f'{p:x}\n' for p in sorted(pcs)))
    target.unlink(missing_ok=True)
    return f'{len(pcs)} PCs ({len(pcs) - before} new)'


def frames(server, g, rest):
    """Profile N fields; the fields between frames (the swap's count at $5dc08) and the
    game state $73a at the end."""
    n = int(rest or 100)
    target = Path(os.path.abspath('tmp/frames.trace'))
    g.stop()
    try:
        _, trace = profile(g, n, target)
        state = _read(g, '0x73a', 2).hex()
    finally:
        g.cont()
    marks = [i for i, f in enumerate(trace.fields)
             for pc, _, _ in trace.instructions(f) if pc == 0x5dc08]
    target.unlink(missing_ok=True)
    gaps = [b - a for a, b in zip(marks, marks[1:])]
    hist = {k: gaps.count(k) for k in sorted(set(gaps))}
    return f'state {state} frames {len(marks)} gaps {hist}'


def _read(g, addr, n):
    out = g.cmd(f'x/{n}bx {addr}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return bytes(vals[:n])


def mem(server, g, rest):
    addr, n, path = rest.split()
    g.stop()
    try:
        data = _read(g, addr, int(n, 0))
    finally:
        g.cont()
    Path(path).write_bytes(data)
    return f'{len(data)} bytes'


def hits(server, g, rest):
    addr, n, *exprs = rest.split()
    g.stop()
    g.cmd('delete')
    g.cmd(f'break *0x{int(addr, 16):x}')
    lines = []
    try:
        for _ in range(int(n)):
            g.cmd('continue', timeout=120)
            vals = [g.cmd(f'printf "%x\\n", {e}').strip().split()[-1] for e in exprs]
            lines.append(' '.join(vals))
    finally:
        g.cmd('delete')
        g.cont()
    return '\n'.join(lines)


server = game_server('esb', commands={'fire': fire, 'mouse': mouse, 'cover': cover,
                                      'mem': mem, 'hits': hits, 'frames': frames})
if __name__ == '__main__':
    server.main(sys.argv[1:])
