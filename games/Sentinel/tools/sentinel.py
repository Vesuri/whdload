"""The Sentinel gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    python3 tools/sentinel.py serve          boot with DEBUG=1 (common/run.sh options apply);
                                             stops at the game's entry when ENTRY=1
    python3 tools/sentinel.py CMD ...        one command to the running server

Commands (each stops the CPU and leaves it stopped at a vsync, except `go`):

    fields N                 run N fields
    key RAW                  press and release raw key RAW (hex), a field apart, then 2 fields
    hold RAW | release RAW   press or release a raw key, then one field
    click                    the left mouse button, pressed for 3 fields (enters pointer mode)
    mouse DX DY [N]          move the mouse N times (default 1) by DX, DY counts, 2 fields each
    peek ADDR N              N bytes at ADDR, hex
    swaps N                  run N fields one at a time; the fields between buffer swaps
                             (changes of the back-buffer pointer $58C76)
    strips K [FILE]          run until K more pan steps have been shown (a step ends when the
                             pan loop's swap count $17D3 is back at -1 after a swap), at most
                             480 fields in all; after each, the SHA-256 of the front buffer
                             (the 32000 bytes of the displayed buffer); FILE.<n>.bin keeps them
    route [SHOTS]            from the entry (ENTRY=1): the title (400 fields), space, the
                             landscape number (150), return for 0000, its overview (400),
                             return: the landscape's first view is then being drawn. SHOTS
                             (a file stem) keeps a screenshot of each stage
    census N STATE           trace N fields (68000/68020 without MMU only), 50 at a time, and
                             add to STATE (a pickle) every base-memory byte executed and every
                             byte the CPU wrote, with the PCs that executed each instruction;
                             tools/smc_census.py reports the overlap
    pointer X Y              steer the mouse until the pointer ($5F84A x 0..2418, $5F84C y
                             0..2996, up is larger) is at X, Y to a mouse count, or stops at
                             an edge (pointer mode)
    waitfor ADDR HEX MAX     run fields until the bytes at ADDR equal HEX (!HEX: differ from
                             it): 'at N (value)' or 'timeout'
    front                    the SHA-256 prefix of the displayed buffer
    brk ADDR SECONDS         run to a breakpoint at ADDR, bounded in wall time: 'hit' or
                             'timeout', with the fields that passed
    snap N FILE [ADDR:LEN ...]
                             run N fields one at a time and append after each the bytes of
                             each range (default the game's variables $1000:$1000 and the
                             program BASE:$8000) to FILE: the per-field state
                             (tools/gametime.sh takes $1700:$100, the field counter and
                             the Sentinel's heading)
    go                       resume

Addresses are the game's runtime ones: the program is loaded at BASE $57FE4 in base memory,
whatever the machine. See docs/development.md for the route and the checks built on these.
"""
import hashlib
import os
import re
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

BASE = 0x57fe4
ENTRY = BASE + 0x10d4
BACK = 0x58c76            # the back buffer, $60000 or $78000
BUFFERS = (0x60000, 0x78000)
BUFFER_SIZE = 4 * 8000
STEPS = 0x17d3            # the pan step's swaps left, -1 between steps


def peek(g, addr, n):
    out = g.cmd(f'x/{n}xb {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    if len(vals) < n:
        raise RuntimeError(f'peek {addr:#x} {n}: {out!r}')
    return bytes(vals[:n])


def long(g, addr):
    return int.from_bytes(peek(g, addr, 4), 'big')


def read_block(g, addr, n, path):
    g.cmd(f'dump binary memory {path} {addr:#x} {addr + n:#x}')
    return Path(path).read_bytes()


def fields(server, g, rest):
    g.stop()
    g.cmd(f'monitor fields {int(rest)}', timeout=600)
    return 'ok'


def key(server, g, rest):
    g.stop()
    g.cmd(f'monitor key {rest} 1')
    g.cmd('monitor fields 1')
    g.cmd(f'monitor key {rest} 0')
    g.cmd('monitor fields 2')
    return 'ok'


def hold(server, g, rest):
    g.stop()
    g.cmd(f'monitor key {rest} 1')
    g.cmd('monitor fields 1')
    return 'held'


def release(server, g, rest):
    g.stop()
    g.cmd(f'monitor key {rest} 0')
    g.cmd('monitor fields 1')
    return 'released'


def click(server, g, rest):
    g.stop()
    g.cmd('monitor input JOY1_FIRE_BUTTON 1')
    g.cmd('monitor fields 3')
    g.cmd('monitor input JOY1_FIRE_BUTTON 0')
    g.cmd('monitor fields 3')
    return 'ok'


def mouse(server, g, rest):
    w = rest.split()
    dx, dy, n = int(w[0]), int(w[1]), int(w[2]) if len(w) > 2 else 1
    g.stop()
    for _ in range(n):
        g.cmd(f'monitor mouse {dx} {dy}')
        g.cmd('monitor fields 2')
    return 'ok'


def peek_cmd(server, g, rest):
    g.stop()
    a, n = rest.split()
    return peek(g, int(a, 0), int(n, 0)).hex()


def swaps(server, g, rest):
    n = int(rest)
    g.stop()
    last, seen = long(g, BACK), []
    for i in range(n):
        g.cmd('monitor fields 1')
        b = long(g, BACK)
        if b != last:
            seen.append(i)
            last = b
    gaps = [b - a for a, b in zip(seen, seen[1:])]
    return f'fields {n} swaps {len(seen)} first {seen[:1]} gaps {gaps}'


def strips(server, g, rest):
    w = rest.split()
    k, stem = int(w[0]), (w[1] if len(w) > 1 else None)
    g.stop()
    tmp = os.path.join(server.run_dir, 'front.bin')
    last, count, out, since, swapped = long(g, BACK), 0, [], 0, False
    while len(out) < k:
        g.cmd('monitor fields 1')
        since += 1
        b = long(g, BACK)
        if b != last:
            count += 1
            last = b
            swapped = True
        # a step ends when the pan loop leaves with its swap count $17D3 at -1
        if swapped and peek(g, STEPS, 1)[0] == 0xff:
            swapped = False
            front = BUFFERS[1] if b == BUFFERS[0] else BUFFERS[0]
            data = read_block(g, front, BUFFER_SIZE, tmp)
            n = len(out) + 1
            if stem:
                Path(f'{stem}.{n}.bin').write_bytes(data)
            out.append(f'{n} {since} {hashlib.sha256(data).hexdigest()[:16]}')
            since = 0
        if since > 60 * 8:
            out.append(f'stalled after {count} swaps')
            break
    return '\n'.join(out)


def front(server, g, rest):
    g.stop()
    b = long(g, BACK)
    data = read_block(g, BUFFERS[1] if b == BUFFERS[0] else BUFFERS[0], BUFFER_SIZE,
                      os.path.join(server.run_dir, 'front.bin'))
    return hashlib.sha256(data).hexdigest()[:16]


ROUTE = (('title', 400, '40'), ('number', 150, '44'), ('overview', 400, '44'))


def route(server, g, rest):
    stem = rest.strip()
    g.stop()
    for name, n, raw in ROUTE:
        g.cmd(f'monitor fields {n}', timeout=600)
        if stem:
            server.handle(g, f'shot {stem}-{name}.png')
        key(server, g, raw)
    return 'landscape 0000'


DMA_RECORD = 58          # the profiler's DMA record: reg u16 @0, addr u32 @12, type @29, data @31


def census(server, g, rest):
    import pickle
    import struct
    from amigaxdev import barto
    import capstone
    w = rest.split()
    n, state = int(w[0]), w[1]
    st = pickle.load(open(state, 'rb')) if os.path.exists(state) else \
        {'exec': {}, 'write': set(), 'fields': 0}
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000 | capstone.CS_MODE_BIG_ENDIAN)
    chunk = os.path.join(server.run_dir, 'census.bin')
    left = n
    while left > 0:
        k = min(50, left)
        server.capture(g, k, chunk)
        t = barto.load(chunk)
        mem = bytearray(t.chip)
        sizes = {}
        for f in t.fields:
            d = bytes(f.dma)
            for i in range(0, len(d), DMA_RECORD):
                reg = d[i] | d[i + 1] << 8
                if d[i + 29] == 2 and reg >> 8 == 0x11:
                    a = struct.unpack_from('<I', d, i + 12)[0]
                    if a < 0x80000:
                        for b in range(reg & 7):
                            st['write'].add(a + b)
            for pc, cost, regs in t.instructions(f):
                if pc is None or pc == 0x7fffffff or pc >= 0x80000:
                    continue
                if pc not in sizes:
                    ins = next(md.disasm(bytes(mem[pc:pc + 10]), pc), None)
                    sizes[pc] = ins.size if ins else 2
                st['exec'].setdefault(pc, sizes[pc])
        st['fields'] += len(t.fields)
        os.unlink(chunk)
        left -= k
    pickle.dump(st, open(state, 'wb'))
    return f"census: {st['fields']} fields, {len(st['exec'])} instructions, {len(st['write'])} bytes written"


def word(g, addr):
    return int.from_bytes(peek(g, addr, 2), 'big')


POINTER = (0x5f84a, 0x5f84c)   # the pointer, x 0..2418 and y, in pointer mode


def pointer(server, g, rest):
    """Steer the mouse (native input, 2 fields a move) until the game's pointer is within a
    mouse count of X, Y (4 in x, 8 in y), or stops moving (an edge)."""
    tx, ty = (int(v, 0) for v in rest.split())
    g.stop()
    x, y = word(g, POINTER[0]), word(g, POINTER[1])
    for _ in range(80):
        dx, dy = tx - x, ty - y
        # a mouse count moves x by +4 and y by -8 (y grows upwards on the screen)
        mx, my = max(-60, min(60, round(dx / 4))), max(-60, min(60, round(-dy / 8)))
        if mx == 0 and my == 0:
            break
        g.cmd(f'monitor mouse {mx} {my}')
        g.cmd('monitor fields 2')
        nx, ny = word(g, POINTER[0]), word(g, POINTER[1])
        if (nx, ny) == (x, y):
            break
        x, y = nx, ny
    return f'pointer {x} {y}'


def waitfor(server, g, rest):
    """Run fields one at a time until the bytes at ADDR equal HEX (or differ from it, !HEX),
    at most MAX fields."""
    a, want, n = rest.split()
    neg = want.startswith('!')
    a, want, n = int(a, 0), bytes.fromhex(want.lstrip('!')), int(n)
    g.stop()
    for i in range(n + 1):
        if (peek(g, a, len(want)) == want) != neg:
            return f'at {i} ({peek(g, a, len(want)).hex()})'
        g.cmd('monitor fields 1')
    return f'timeout {n} ({peek(g, a, len(want)).hex()})'


VBL = 0x58c6e                  # the game's field counter


def brk(server, g, rest):
    """Run to a breakpoint at ADDR for at most SECONDS of wall time; stays stopped there (or
    wherever the time ran out). Prints hit or timeout and the fields that passed."""
    a, secs = rest.split()
    g.stop()
    v0 = word(g, VBL)
    g.cmd(f'break *{a}')
    try:
        out = g.cmd('continue', timeout=float(secs))
        hit = 'Breakpoint' in out
    except TimeoutError:
        os.kill(g.p.pid, signal.SIGINT)     # a synchronous continue reads no stdin
        g.read_until(g.sent, 30)            # then gdb runs the echo queued after it
        hit = False
    g.cmd('delete')
    return f"{'hit' if hit else 'timeout'} {(word(g, VBL) - v0) & 0xffff}"


SNAP = ((0x1000, 0x1000), (BASE, 0x8000))


def snap(server, g, rest):
    w = rest.split()
    n, path = int(w[0]), w[1]
    ranges = [tuple(int(v, 16) for v in r.split(':')) for r in w[2:]] or SNAP
    g.stop()
    tmp = os.path.join(server.run_dir, 'snap.bin')
    with open(path, 'ab') as f:
        for _ in range(n):
            g.cmd('monitor fields 1')
            for a, k in ranges:
                f.write(read_block(g, a, k, tmp))
    return f'snap {n} fields, {sum(k for _, k in ranges)} bytes each'


def go(server, g, rest):
    g.cont()
    return 'running'


server = game_server('sentinel', commands={
    'fields': fields, 'key': key, 'click': click, 'mouse': mouse, 'hold': hold, 'release': release, 'peek': peek_cmd,
    'swaps': swaps, 'strips': strips, 'route': route, 'census': census, 'pointer': pointer, 'front': front, 'waitfor': waitfor, 'brk': brk,
    'snap': snap, 'go': go})

if __name__ == '__main__':
    if sys.argv[1:2] == ['serve'] and os.environ.get('ENTRY') == '1':
        os.environ['BOOT_BREAK'] = hex(ENTRY)
    server.main(sys.argv[1:])
