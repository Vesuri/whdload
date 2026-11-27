"""Empire Strikes Back gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/esb.py serve               boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/esb.py wait 20             then shot, quit, ...
    python3 tools/esb.py fire N              hold the trigger (left mouse button) N fields
    python3 tools/esb.py mouse DX DY [N]     move the mouse by DX, DY a field, N fields
    python3 tools/esb.py key CODE [N]        hold the raw key CODE (hex) N fields (5)
    python3 tools/esb.py sweep [N]           N fields (250): sweep the crosshair, firing
    python3 tools/esb.py frames [N]          profile N fields (100): fields between frames
    python3 tools/esb.py span A B N          N times: the raster lines from A to B (hex)
    python3 tools/esb.py cover N FILE        profile N fields; add every PC executed in the
                                             game image ($500-$5e500) to FILE (one hex
                                             address a line, kept sorted)
    python3 tools/esb.py mem ADDR LEN FILE   LEN bytes at ADDR (gdb syntax) to FILE
    python3 tools/esb.py hits ADDR N EXPR... stop N times at ADDR (hex) and print each EXPR
    python3 tools/esb.py incl N FILE         profile N fields; inclusive CPU cycles of each
                                             routine called in the game image to FILE
                                             (FILE with .excl: each one's own cycles; .pcs:
                                             by 64-byte block)
    python3 tools/esb.py sm [BUILD]          the enhanced framerate's state and statistics
                                             (SmV, by the BUILD's listing: verify)
    python3 tools/esb.py gdb CMD...          stop, run each gdb command (separated by ;), go on
    python3 tools/esb.py calls N FILE        profile N fields; every call (jsr, bsr) made in
                                             the game image to FILE: callee, caller, count

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


def keyspan(server, g, rest):
    """CODE A B [N]: hold the raw key CODE through a profile of N fields (20); each run
    from PC A to the next PC B, in raster lines (its traced cost over the field's)."""
    code, a, b, *n = rest.split()
    a, b = int(a, 16), int(b, 16)
    target = Path(os.path.abspath('tmp/keyspan.trace'))
    g.stop()
    try:
        g.cmd(f'monitor key {int(code, 16):x} 1')     # held through the trace
        try:
            _, trace = profile(g, int(n[0]) if n else 20, target)
        finally:
            g.cmd(f'monitor key {int(code, 16):x} 0')
    finally:
        g.cont()
    target.unlink(missing_ok=True)
    out, start = [], None
    for f in trace.fields:
        per_line = f.cycles / 312.5
        for pc, cost, _ in trace.instructions(f):
            if pc == a and start is None:
                start = 0.0
            if start is not None:
                if pc == b:
                    out.append(f'{start / per_line:.2f}')
                    start = None
                elif cost is not None:
                    start += cost
    return 'lines ' + ' '.join(out)


def key(server, g, rest):
    """KEY (raw code, hex) held N fields (5)."""
    code, *n = rest.split()
    g.stop()
    g.cmd(f'monitor key {int(code, 16):x} 1')
    g.cmd(f'monitor fields {int(n[0]) if n else 5}')
    g.cmd(f'monitor key {int(code, 16):x} 0')
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


def sweep(server, g, rest):
    """N fields of play: the crosshair swept across the screen, firing on and off."""
    n = int(rest or 250)
    g.stop()
    try:
        for i in range(n):
            dx = 6 if (i // 48) % 2 == 0 else -6
            dy = 3 if (i // 28) % 2 == 0 else -3
            g.cmd(f'monitor mouse {dx} {dy}')
            g.cmd(f'monitor input JOY1_FIRE_BUTTON {1 if i % 8 < 4 else 0}')
            g.cmd('monitor fields 1')
        g.cmd('monitor input JOY1_FIRE_BUTTON 0')
    finally:
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
    """Profile N fields; the fields between frames (the swap's entry $5dc02, run by the
    enhanced framerate's hook too) and the game state $73a at the end."""
    n = int(rest or 100)
    target = Path(os.path.abspath('tmp/frames.trace'))
    g.stop()
    try:
        _, trace = profile(g, n, target)
        state = _read(g, '0x73a', 2).hex()
    finally:
        g.cont()
    marks = [i for i, f in enumerate(trace.fields)
             for pc, _, _ in trace.instructions(f) if pc == 0x5dc02]
    target.unlink(missing_ok=True)
    gaps = [b - a for a, b in zip(marks, marks[1:])]
    hist = {k: gaps.count(k) for k in sorted(set(gaps))}
    return f'state {state} frames {len(marks)} gaps {hist}'


def _is_call(chip, pc):
    if pc is None or not 0x500 <= pc < 0x5e500:
        return False
    w = int.from_bytes(chip[pc:pc + 2], 'big')
    return (w & 0xffc0) == 0x4e80 or (w & 0xff00) == 0x6100


def calls(server, g, rest):
    n, path = rest.split()
    path = Path(os.path.abspath(path))
    target = path.with_suffix('.trace')
    g.stop()
    try:
        _, trace = profile(g, int(n), target)
    finally:
        g.cont()
    count = {}
    for f in trace.fields:
        prev = None
        for pc, _, _ in trace.instructions(f):
            if pc is None or pc == 0x7fffffff:
                continue
            if prev is not None and _is_call(trace.chip, prev):
                count[(pc, prev)] = count.get((pc, prev), 0) + 1
            prev = pc
    target.unlink(missing_ok=True)
    path.write_text(''.join(f'{c:x} {a:x} {k}\n' for (c, a), k in sorted(count.items())))
    return f'{len(count)} call sites'


def incl(server, g, rest):
    """Inclusive cost per callee (by the stack: a call pushes the callee and A7, an
    instruction with A7 above it pops it)."""
    n, path = rest.split()
    path = Path(os.path.abspath(path))
    target = path.with_suffix('.trace')
    g.stop()
    try:
        _, trace = profile(g, int(n), target)
    finally:
        g.cont()
    tot, cnt, ex, pcs, total = {}, {}, {}, {}, 0
    for f in trace.fields:
        stack, prev = [], None
        for pc, cost, r in trace.instructions(f):
            if pc is None or pc == 0x7fffffff or cost is None:
                continue
            sp = r[15]
            if prev is not None and _is_call(trace.chip, prev):
                stack.append((pc, sp))
                cnt[pc] = cnt.get(pc, 0) + 1
            while stack and sp > stack[-1][1]:
                stack.pop()
            total += cost
            top = stack[-1][0] if stack else 0
            ex[top] = ex.get(top, 0) + cost
            pcs[pc & ~63] = pcs.get(pc & ~63, 0) + cost
            for e in {e for e, _ in stack}:
                tot[e] = tot.get(e, 0) + cost
            prev = pc
    target.unlink(missing_ok=True)
    path.write_text(f'total {total}\n' + ''.join(
        f'{e:x} {c} {c * 100 / total:.1f}% calls {cnt[e]}\n'
        for e, c in sorted(tot.items(), key=lambda x: -x[1])))
    path.with_suffix('.excl').write_text(''.join(
        f'{e:x} {c} {c * 100 / total:.1f}%\n'
        for e, c in sorted(ex.items(), key=lambda x: -x[1])))
    path.with_suffix('.pcs').write_text(''.join(
        f'{e:x} {c} {c * 100 / total:.1f}%\n'
        for e, c in sorted(pcs.items(), key=lambda x: -x[1])))
    return f'{len(tot)} routines'


def _sv_fields():
    """(name, offset, size) of the SmV structure, from its RS block in the source."""
    import re
    src = Path(__file__).resolve().parents[1] / 'src/EmpireStrikesBackSmooth.s'
    text = src.read_text()
    consts = {k: int(v) for k, v in re.findall(r'^(SM_[A-Z]+)\s*=\s*(\d+)', text, re.M)}
    out, off = [], 0
    for name, size, count in re.findall(r'^(sv_\w+)\s+rs\.([bwl])\s+([\w*+]+)', text, re.M):
        n = eval(count, {}, consts)
        sz = {'b': 1, 'w': 2, 'l': 4}[size]
        if size != 'b' and off % 2:
            off += 1
        out.append((name, off, sz, n))
        off += sz * n
    return out


def sm(server, g, rest):
    import re
    import struct
    build = rest.strip() or 'verify'
    lst = Path(__file__).resolve().parents[1] / f'tmp/build/{build}/EmpireStrikesBack.lst'
    text = lst.read_text(errors='replace')

    def sym(name):
        m = re.search(r'^([0-9A-F]{8}) ' + name + r'$', text, re.M)
        return int(m.group(1), 16)
    g.stop()
    try:
        swap = struct.unpack('>I', _read(g, '0x5dc04', 4))[0]
        base = swap - sym('SmSwap')
        sv = base + sym('SmV')
        fields = _sv_fields()
        size = fields[-1][1] + fields[-1][2] * fields[-1][3]
        g.cmd(f'dump binary memory tmp/sv.bin {sv} {sv + size}')
        data = Path('tmp/sv.bin').read_bytes()
        now = int.from_bytes(_read(g, hex(base + sym('_FixFields')), 2), 'big')
    finally:
        g.cont()
    rows = [f'slave {base:#x} SmV {sv:#x}']
    off = {name: o for name, o, _, _ in _sv_fields()}
    ticks = int.from_bytes(data[off['sv_all']:off['sv_all'] + 4], 'big')
    f0 = int.from_bytes(data[off['sv_f0']:off['sv_f0'] + 4], 'big')
    if ticks > 1:
        rows.append(f'fields a tick {((now - f0) & 0xffff) / (ticks - 1):.2f} '
                    f'({ticks} ticks)')
    for name, off, sz, n in fields:
        if name in ('sv_tcost', 'sv_tcnt', 'sv_bhist'):
            vals = [int.from_bytes(data[off + 4 * i:off + 4 * i + 4], 'big') for i in range(n)]
            rows.append(f'{name} {vals}')
            continue
        if name in ('sv_stn', 'sv_stbad'):
            vals = [int.from_bytes(data[off + 2 * i:off + 2 * i + 2], 'big') for i in range(n)]
            rows.append(f'{name} ' + ' '.join(f'{i:02x}:{v}' for i, v in enumerate(vals) if v))
            continue
        if n != 1 or name in ('sv_regs', 'sv_keys'):
            continue
        v = int.from_bytes(data[off:off + sz], 'big')
        rows.append(f'{name} {v:#x} ({v})')
    return '\n'.join(rows)


def gdb(server, g, rest):
    g.stop()
    try:
        return '\n'.join(g.cmd(c.strip()) for c in rest.split(';'))
    finally:
        g.cont()


def _read(g, addr, n):
    out = g.cmd(f'x/{n}bx {addr}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return bytes(vals[:n])


def mem(server, g, rest):
    addr, n, path = rest.split()
    path = os.path.abspath(path)
    g.stop()
    try:
        a = int(g.cmd(f'printf "%u\\n", {addr}').split()[-1])
        g.cmd(f'dump binary memory {path} {a} {a + int(n, 0)}', timeout=300)
    finally:
        g.cont()
    return f'{os.path.getsize(path)} bytes'


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


def span(server, g, rest):
    """N times: stop at A, then at B; the beam (VPOSR/VHPOSR) at each, and the lines
    between."""
    a, b, n = rest.split()
    g.stop()
    g.cmd('delete')
    out = []

    def beam():
        v = int(g.cmd('printf "%u\\n", *(unsigned int *)0xdff004').split()[-1])
        return ((v >> 8) & 0x7ff), v & 0xff     # line (V8-V0 plus LOF bits masked), h

    try:
        for _ in range(int(n)):
            g.cmd(f'break *0x{int(a, 16):x}')
            g.cmd('continue', timeout=120)
            g.cmd('delete')
            l0, h0 = beam()
            g.cmd(f'break *0x{int(b, 16):x}')
            g.cmd('continue', timeout=120)
            g.cmd('delete')
            l1, h1 = beam()
            l0 &= 0x1ff
            l1 &= 0x1ff
            d = (l1 - l0) % 313 + (h1 - h0) / 227
            out.append(f'{l0}:{h0} -> {l1}:{h1}  {d:.2f} lines')
    finally:
        g.cmd('delete')
        g.cont()
    return '\n'.join(out)


server = game_server('esb', commands={'fire': fire, 'mouse': mouse, 'sweep': sweep, 'cover': cover,
                                      'mem': mem, 'hits': hits, 'frames': frames, 'span': span, 'key': key, 'keyspan': keyspan,
                                      'calls': calls, 'incl': incl, 'sm': sm,
                                      'gdb': gdb})
if __name__ == '__main__':
    server.main(sys.argv[1:])
