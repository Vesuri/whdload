"""Star Wars gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/starwars.py serve          boot with DEBUG=1 (common/run.sh options apply)
    python3 tools/starwars.py wait 20        then shot, quit, ...
    python3 tools/starwars.py base           the code hunk's and a4's runtime addresses
    python3 tools/starwars.py hits OFF N EXPR...
                                             stop N times at code-hunk offset OFF (hex) and
                                             print each EXPR (gdb syntax; `A4` and `CODE`
                                             stand for the runtime bases)
    python3 tools/starwars.py fire N         hold the trigger (left mouse button) N fields
    python3 tools/starwars.py probe          the VERIFY build's work timer per paced loop
    python3 tools/starwars.py smooth         the smooth mode's (CUSTOM2) counters
    python3 tools/starwars.py seq N PREFIX   screenshots of N consecutive fields,
                                             PREFIX00.png ...
    python3 tools/starwars.py code FILE      the patched code hunk ($e9e8 bytes) to FILE
    python3 tools/starwars.py mouse DX DY [N]
                                             move the mouse by DX, DY a field, N fields
    python3 tools/starwars.py pc             the PC and the code-hunk return addresses on
                                             the stack, as code-hunk offsets
    python3 tools/starwars.py mem EXPR LEN FILE
                                             LEN bytes at EXPR (gdb syntax, `A4`, `CODE`)
                                             to FILE
    python3 tools/starwars.py recdump PREFIX [N]
                                             VERIFY build: at the next N (1) SmRender
                                             entries, the current and the previous
                                             recording (pairs filled) to PREFIXkk.cur,
                                             PREFIXkk.prev and sv_ok, a tick apart
    python3 tools/starwars.py reach OFF      run until code-hunk offset OFF (hex), stay stopped
    python3 tools/starwars.py sweep DX DY N PREFIX [SKIP]
                                             N times: move the mouse by DX, DY, run SKIP
                                             fields (0), screenshot one, PREFIX00.png ...;
                                             the emulator stays stopped in between

Addresses in commands are code-hunk offsets; the program's globals are a4-relative
(`A4-26430` is the frame counter). a4 is the data hunk + $7ffe, and the jump table's
first entry (at a4-32766) holds the relocated code hunk base.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402


def _bases(g):
    g.stop()
    a4 = int(g.cmd('printf "%u\\n", $a4').split()[-1])
    code = int(g.cmd(f'printf "%u\\n", *(unsigned int *){a4 - 32766 + 2}').split()[-1])
    return code, a4


def _subst(expr, code, a4):
    return expr.replace('CODE', str(code)).replace('A4', str(a4))


def base(server, g, rest):
    code, a4 = _bases(g)
    g.cont()
    return f'code {code:#x} a4 {a4:#x} data {a4 - 0x7ffe:#x}'


def _slave_base(g, code):
    """The slave's runtime base: the patched jsr at $897e (+2) goes to SmPresent3a, whose
    offset the VERIFY build's listing gives."""
    import re
    import struct
    lst = Path(__file__).resolve().parents[1] / 'tmp/build/verify/StarWars.lst'
    m = re.search(rb'^SmPresent3a +00:([0-9A-F]+)', lst.read_bytes(), re.M)
    tgt = struct.unpack('>I', _read(g, code + 0x8980, 4))[0]
    return tgt - int(m.group(1), 16)


def hits(server, g, rest):
    """OFF: a code-hunk offset, or sOFF a VERIFY slave offset (its listing); `SLV` in
    the expressions stands for the slave's base."""
    off, n, *exprs = rest.split()
    code, a4 = _bases(g)
    slv = _slave_base(g, code) if off.startswith('s') or any('SLV' in e for e in exprs) else 0
    exprs = [e.replace('SLV', str(slv)) for e in exprs]
    g.cmd('delete')
    g.cmd(f'break *{(slv + int(off[1:], 16)) if off.startswith("s") else code + int(off, 16)}')
    rows = []
    for _ in range(int(n)):
        out = g.cmd('continue', timeout=600)
        if 'Breakpoint' not in out:
            rows.append('stopped: ' + out.splitlines()[-1])
            break
        vals = []
        for e in exprs:
            r = g.cmd(f'printf "%d\\n", {_subst(e, code, a4)}')
            vals.append(r.split()[-1] if r else '?')
        rows.append(' '.join(vals))
    g.cmd('delete')
    g.cont()
    return '\n'.join(rows)


def fire(server, g, rest):
    g.stop()
    g.cmd('monitor input JOY1_FIRE_BUTTON 1')
    g.cmd(f'monitor fields {int(rest or 5)}')
    g.cmd('monitor input JOY1_FIRE_BUTTON 0')
    g.cont()
    return 'ok'


def _read(g, addr, n):
    """n bytes at addr as bytes, through gdb's x/bx."""
    out = g.cmd(f'x/{n}xb {addr}', timeout=120)
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    return bytes(vals[:n])


SITES = ('space $897e', 'surface-in $b612', 'surface $b65e', 'trench $d5a8')


def probe(server, g, rest):
    """The VERIFY work timer (src/StarWarsProbe.s), per paced site."""
    import struct
    code, a4 = _bases(g)
    tgt = struct.unpack('>I', _read(g, code + 0x8980, 4))[0]
    back = _read(g, tgt - 128, 128)
    i = back.rfind(b'SWPB')
    if i < 0:
        g.cont()
        return 'no probe (not a VERIFY build?)'
    buf = struct.unpack('>I', back[i + 4:i + 8])[0]
    raw = _read(g, buf, 176 * 4)
    g.cont()
    rows = []
    for k, name in enumerate(SITES):
        r = raw[176 * k:176 * (k + 1)]
        n, total, mx = struct.unpack('>III', r[:12])
        frames = struct.unpack('>8I', r[12:44])
        hist = struct.unpack('>32I', r[44:172])
        if not n:
            rows.append(f'{name}: no passes')
            continue
        # percentiles from the 32-line buckets (upper edge)
        def pct(p):
            c = 0
            for b, h in enumerate(hist):
                c += h
                if c >= p * n:
                    return (b + 1) * 32
            return 32 * 32
        rows.append(f'{name}: passes {n} mean {total / n:.0f} lines ({total / n * 0.064:.1f} ms) '
                    f'p50<{pct(.5)} p95<{pct(.95)} max {mx}; frames at wait {list(frames)}')
    return '\n'.join(rows)


SV = ('buf cur prev ptr end pend b0 f0 vp0 vp1 vp2 vbuf tmp0 tmp1 obj_r flags '
      'maxops ovf ticks frames paired unpaired fields j0 j1 j2 j3 rl0').split() + [f'h{i}' for i in range(16)] + 'rmax x0 x1 shown ready t_base lastt_lastc hudcopies dir_slow_hold l0 work dticks hooked_saved_ravg worksum late_lates chipfree n_mul thr_call exact_prec_cstart rel_pad dropped'.split()


def smooth(server, g, rest):
    """The smooth mode's statistics (sv_* in src/StarWarsSmooth.s)."""
    import struct
    code, a4 = _bases(g)
    tgt = struct.unpack('>I', _read(g, code + 0x8980, 4))[0]
    fwd = _read(g, tgt, 4096)
    i = fwd.find(b'SWSM')
    if i < 0:
        g.cont()
        return 'no SWSM tag (smooth mode not patched?)'
    raw = _read(g, tgt + i + 4, len(SV) * 4)
    g.cont()
    v = dict(zip(SV, struct.unpack(f'>{len(SV)}I', raw)))
    used = (v['ptr'] - v['cur']) // 16 if v['buf'] else 0
    return (f"buf {v['buf']:#x} ops now {used} max {v['maxops']} overflows {v['ovf']} "
            f"ticks {v['ticks']} frames {v['frames']} paired {v['paired']} "
            f"unpaired {v['unpaired']} fields {v['fields']} first-frame field {[v[k] for k in ('j0','j1','j2','j3')]} render lines hist/32 {[v[f'h{i}'] for i in range(16)]} max {v['rmax']} screens {v['x0']:#x} {v['x1']:#x} chipfree {v['chipfree']} hudcopies {v['hudcopies']} direct {v['dir_slow_hold'] >> 24} dticks {v['dticks']} work {v['work']} mean work {v['worksum'] // max(1, v['dticks'])} ravg {(v['hooked_saved_ravg'] & 0xffff) // 8} late ticks {v['late_lates'] & 0xffff} dropped {v['dropped']} r {v['obj_r'] & 0xffff} flags {v['flags']:#010x}")


def seq(server, g, rest):
    """N consecutive fields' screenshots (one trace of N fields)."""
    import os
    from amigaxdev.gdbserve import profile
    n, prefix = rest.split(None, 1)
    target = os.path.join(server.run_dir, 'seq.bin')
    g.stop()
    try:
        _, trace = profile(g, int(n), target)
    finally:
        g.cont()
    out = []
    for i, f in enumerate(trace.fields):
        if f.shot:
            png = f'{os.path.abspath(prefix)}{i:02d}.png'
            with open(png, 'wb') as fh:
                fh.write(f.shot)
            out.append(png)
    os.remove(target)
    return f'{len(out)} shots'


def mouse(server, g, rest):
    dx, dy, *n = rest.split()
    g.stop()
    for _ in range(int(n[0]) if n else 1):
        g.cmd(f'monitor mouse {int(dx)} {int(dy)}')
        g.cmd('monitor fields 1')
    g.cont()
    return 'ok'


def pc(server, g, rest):
    import struct
    c, _ = _bases(g)
    p = int(g.cmd('printf "%u\\n", $pc').split()[-1])
    sp = int(g.cmd('printf "%u\\n", $sp').split()[-1])
    words = struct.unpack('>64I', _read(g, sp, 256))
    g.cont()
    rets = [f'{w - c:x}' for w in words if c <= w < c + CODE_SIZE]
    where = f'{p - c:x}' if c <= p < c + CODE_SIZE else f'abs {p:x}'
    return f'pc {where} stack {" ".join(rets[:10])}'


def _lst(name):
    import re
    lst = Path(__file__).resolve().parents[1] / 'tmp/build/verify/StarWars.lst'
    m = re.search(rb'^' + name.encode() + rb' +00:([0-9A-F]+)', lst.read_bytes(), re.M)
    return int(m.group(1), 16)


def recdump(server, g, rest):
    import os
    import struct
    prefix, *n = rest.split()
    code, a4 = _bases(g)
    slv = _slave_base(g, code)
    sv = slv + _lst('SmV')
    g.cmd('delete')
    g.cmd(f'break *{slv + _lst("SmRender")}')
    out = []
    last = None
    k = 0
    while k < (int(n[0]) if n else 1):
        r = g.cmd('continue', timeout=600)
        if 'Breakpoint' not in r:
            out.append('stopped')
            break
        cur, prev, ptr, _, pend = struct.unpack('>5I', _read(g, sv + 4, 20))
        ok = _read(g, sv + 61, 1)[0]
        if cur == last:
            continue                    # another frame of the same tick
        last = cur
        for suf, a, b in (('cur', cur, ptr), ('prev', prev, pend)):
            path = os.path.abspath(f'{prefix}{k:02d}.{suf}')
            g.cmd(f'dump binary memory {path} {a} {max(a, b)}', timeout=120)
        out.append(f'{k}: ops {(ptr - cur) // 16} prev {(pend - prev) // 16} ok {ok}')
        k += 1
    g.cmd('delete')
    g.cont()
    return '\n'.join(out)


def reach(server, g, rest):
    code, _ = _bases(g)
    g.cmd('delete')
    g.cmd(f'break *{code + int(rest, 16)}')
    out = g.cmd('continue', timeout=600)
    g.cmd('delete')
    return 'reached' if 'Breakpoint' in out else 'stopped: ' + out.splitlines()[-1]


def sweep(server, g, rest):
    import os
    from amigaxdev.gdbserve import profile
    dx, dy, n, prefix, *skip = rest.split()
    target = os.path.join(server.run_dir, 'sweep.bin')
    g.stop()
    try:
        for i in range(int(n)):
            g.cmd(f'monitor mouse {int(dx)} {int(dy)}')
            if skip and int(skip[0]):
                g.cmd(f'monitor fields {int(skip[0])}')
            _, trace = profile(g, 1, target)
            with open(f'{os.path.abspath(prefix)}{i:02d}.png', 'wb') as fh:
                fh.write(trace.fields[-1].shot)
    finally:
        g.cont()
    os.remove(target)
    return f'{n} shots'


CODE_SIZE = 0xe9e8


def mem(server, g, rest):
    import os
    expr, n, path = rest.split()
    c, a4 = _bases(g)
    a = int(g.cmd(f'printf "%u\\n", (unsigned int)({_subst(expr, c, a4)})').split()[-1])
    path = os.path.abspath(path)
    g.cmd(f'dump binary memory {path} {a} {a + int(n, 0)}', timeout=120)
    g.cont()
    return f'{a:#x} {os.path.getsize(path)} bytes'


def code(server, g, rest):
    """The code hunk as the game runs it, patched, to a file."""
    import os
    c, _ = _bases(g)
    path = os.path.abspath(rest.strip())
    g.cmd(f'dump binary memory {path} {c} {c + CODE_SIZE}', timeout=120)
    g.cont()
    return f'{os.path.getsize(path)} bytes'


server = game_server('starwars', commands={'base': base, 'hits': hits, 'fire': fire,
                                           'probe': probe, 'smooth': smooth,
                                           'seq': seq, 'code': code,
                                           'mouse': mouse, 'sweep': sweep,
                                           'reach': reach, 'pc': pc,
                                           'mem': mem, 'recdump': recdump})
if __name__ == '__main__':
    server.main(sys.argv[1:])
