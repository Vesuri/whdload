"""Alien Breed 3D gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    INSTANCE=x WARP=1 WINDOW=none python3 tools/ab3d.py serve &   boot (common/run.sh options)
    python3 tools/ab3d.py CMD ...                                  one command to the server

Game commands (game offsets as in docs/internals.md, $c4dc version; the CPU is left as it
was found, running or stopped):
    base                  where the hunks are: hunk 0 and the chip hunks' runtime addresses
    peek OFF [N]          N bytes (default 4) at game offset OFF, hex
    level                 from the main menu into level 1: RETURN every 100 fields until the
                          first frames, then M (mouse control)
    full [0|1]            the view: print it, or press keypad Enter until it is the one asked
                          (0 small, 1 full screen)
    frames [N]            run N fields (default 500) one at a time and count the frames shown:
                          swaps of drawPt (offset $5dd40), which the main loop makes once a
                          frame after a vertical-blank wait. Reports fps and fields a frame
                          (p50, p95, max)
    play SCRIPT           run an input script: steps separated by ';', each
                          `F [mx MX] [my MY] [fire]`: F fields with the mouse moved MX, MY a
                          field (forward is my -N) and the button held; or a name from
                          SCRIPTS (`play walk`, the baseline's scripted walk)
    batch CMD ;; CMD      gdb commands in one request, CPU stopped

The 8-channel ($c4dc) version only, which the AGA drawer installs.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

FLAT = Path(__file__).resolve().parents[1] / 'tmp/exe/abd.flat'
# hunk sizes of the $c4dc version (tools/exe.py): code and data, then three chip hunks
HUNKS = (0x912d4, 0x9f64, 0x18, 0x12798)
DRAWPT = 0x5dd40        # drawPt, the copper list being drawn; oldDrawPt follows
FULL = 0x40279          # nonzero in full screen (flipped by keypad Enter)
KEY_RETURN, KEY_M, KEY_ENTER = 0x44, 0x37, 0x43


def _bytes(g, addr, n):
    out = g.cmd(f'x/{n}xb {addr:#x}')
    vals = []
    for line in out.splitlines():
        if ':' in line:
            vals += [int(v, 16) for v in line.split(':', 1)[1].split()]
    if len(vals) < n:
        raise RuntimeError(f'short read at {addr:#x}: {out!r}')
    return bytes(vals[:n])


def _long(g, addr):
    return struct.unpack('>I', _bytes(g, addr, 4))[0]


class Halted:
    """Stop the CPU for a block; resume it after if it was running."""

    def __init__(self, g):
        self.g = g

    def __enter__(self):
        self.was = self.g.running
        self.g.stop()
        return self.g

    def __exit__(self, *exc):
        if self.was:
            self.g.cont()


_bases = {}


def bases(g):
    """Runtime address of each hunk's data. The slave relocates the game in LoadSeg layout
    (each hunk: its allocation size, then the link, a BPTR to the next hunk's link, then the
    data) at ExpMem+$2000, $3000 further on when HackAB3D is loaded before it; the fake
    ExecBase is ExpMem+$1000."""
    key = _long(g, 4)
    if key in _bases:
        return _bases[key]
    expmem = key - 0x1000
    for seg in (expmem + 0x2000 + 0x3000, expmem + 0x2000):
        out, link = [], seg + 4
        for size in HUNKS:
            if not link or _long(g, link - 4) != size + 8:
                break
            out.append(link + 4)
            link = _long(g, link) * 4
        if len(out) == len(HUNKS):
            _bases[key] = out
            return out
    raise RuntimeError(f'game hunks not found from ExecBase {key:#x}: not loaded yet, or '
                       'not the $c4dc version')


def addr(g, off):
    """Game offset to runtime address."""
    start = 0
    for size, base in zip(HUNKS, bases(g)):
        if off < start + size:
            return base + off - start
        start += size
    raise ValueError(f'offset {off:#x} past the last hunk')


def cmd_base(server, g, rest):
    with Halted(g):
        b = bases(g)
        start, lines = 0, []
        for i, (size, a) in enumerate(zip(HUNKS, b)):
            lines.append(f'hunk {i}  offset ${start:06x}  at ${a:08x}  {size} bytes')
            start += size
        if FLAT.exists():
            want = FLAT.read_bytes()[0x1fd4c:0x1fd5c]
            ok = _bytes(g, addr(g, 0x1fd4c), 16) == want
            lines.append('bump-map OneBelow $1fd4c ' + ('matches abd.flat' if ok else 'DIFFERS from abd.flat'))
        return '\n'.join(lines)


def cmd_peek(server, g, rest):
    w = rest.split()
    off, n = int(w[0], 0), int(w[1], 0) if len(w) > 1 else 4
    with Halted(g):
        return _bytes(g, addr(g, off), n).hex()


def _key(g, code, fields=10):
    """Press and release; the game misses a key held only 3 fields."""
    g.cmd(f'monitor key {code:x} 1')
    g.cmd(f'monitor fields {fields}')
    g.cmd(f'monitor key {code:x} 0')
    g.cmd(f'monitor fields {fields}')


def _drawpt(g):
    return _long(g, addr(g, DRAWPT))


def cmd_level(server, g, rest):
    """RETURN every 100 fields (the menu, then the text screen once it has loaded) until
    drawPt swaps; then M."""
    with Halted(g):
        first, presses = _drawpt(g), 0
        for n in range(0, 4000, 10):
            if n % 100 == 0:
                _key(g, KEY_RETURN)
                presses += 1
            g.cmd('monitor fields 10')
            if _drawpt(g) != first:
                break
        else:
            raise RuntimeError('no frame drawn within 4000 fields')
        g.cmd('monitor fields 50')
        _key(g, KEY_M)
        return f'in level 1 after {n + 10} fields and {presses} RETURNs; mouse control on'


def cmd_full(server, g, rest):
    with Halted(g):
        def state():
            return _bytes(g, addr(g, FULL), 1)[0] != 0
        if rest.strip():
            want = rest.strip() == '1'
            for _ in range(3):
                if state() == want:
                    break
                _key(g, KEY_ENTER)
            else:
                raise RuntimeError('keypad Enter did not switch the view')
        return 'full screen' if state() else 'small view'


def _percentile(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def cmd_frames(server, g, rest):
    n = int(rest.split()[0]) if rest.split() else 500
    with Halted(g):
        a = addr(g, DRAWPT)
        last, at, gaps = _long(g, a), None, []
        for i in range(n):
            g.cmd('monitor fields 1')
            p = _long(g, a)
            if p != last:
                if at is not None:
                    gaps.append(i - at)
                at, last = i, p
    if not gaps:
        return f'{n} fields: no complete frame'
    frames = len(gaps)
    mean = sum(gaps) / frames
    return (f'{n} fields: {frames} whole frames, {50 / mean:.2f} fps; fields a frame mean '
            f'{mean:.2f} p50 {_percentile(gaps, .5)} p95 {_percentile(gaps, .95)} max {max(gaps)}')


# Named input scripts for repeatable scenes (game time follows the frame rate, so a script
# ends in the same place only on the same machine).
SCRIPTS = {
    # level 1: down the start corridor, through the door, round the room, back out
    'walk': '200 my -10; 50 mx 20; 100 my -10; 50 mx -20; 100 my -10; 50 mx 30',
}


def cmd_play(server, g, rest):
    rest = SCRIPTS.get(rest.strip(), rest)
    total = 0
    with Halted(g):
        for step in filter(None, (s.strip() for s in rest.split(';'))):
            w = step.split()
            fields, mx, my, fire = int(w[0]), 0, 0, False
            i = 1
            while i < len(w):
                if w[i] == 'mx':
                    mx, i = int(w[i + 1]), i + 2
                elif w[i] == 'my':
                    my, i = int(w[i + 1]), i + 2
                elif w[i] == 'fire':
                    fire, i = True, i + 1
                else:
                    raise ValueError(f'unknown word {w[i]!r} in {step!r}')
            if fire:
                g.cmd('monitor input JOY1_FIRE_BUTTON 1')
            for _ in range(fields):
                if mx or my:
                    g.cmd(f'monitor mouse {mx} {my}')
                g.cmd('monitor fields 1')
            if fire:
                g.cmd('monitor input JOY1_FIRE_BUTTON 0')
            total += fields
    return f'played {total} fields'


def cmd_batch(server, g, rest):
    with Halted(g):
        return ''.join(g.cmd(c, timeout=600).rstrip('\n') + '\n'
                       for c in rest.split(' ;; ') if c.strip())


server = game_server('ab3d', commands={
    'base': cmd_base, 'peek': cmd_peek, 'level': cmd_level, 'full': cmd_full,
    'frames': cmd_frames, 'play': cmd_play, 'batch': cmd_batch})

if __name__ == '__main__':
    server.main(sys.argv[1:])
