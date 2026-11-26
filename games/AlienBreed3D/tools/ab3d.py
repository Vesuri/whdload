"""Alien Breed 3D gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    INSTANCE=x WARP=1 WINDOW=none python3 tools/ab3d.py serve &   boot (common/run.sh options)
    python3 tools/ab3d.py CMD ...                                  one command to the server

Game commands (game offsets as in docs/internals.md, $c4dc version; the CPU is left as it
was found, running or stopped):
    base                  where the hunks are: hunk 0 and the chip hunks' runtime addresses
    peek OFF [N]          N bytes (default 4) at game offset OFF, hex
    level                 from the main menu into level 1: RETURN every 100 fields until the
                          first frames, then M until mouse control is on (PLR1MOUSE)
    full [0|1]            the view: print it, or press keypad Enter until it is the one asked
                          (0 small, 1 full screen)
    frames [N [SCRIPT]]   run N fields (default 500) one at a time, playing SCRIPT, and count
                          the frames shown: swaps of drawPt (offset $5dd40), which the main
                          loop makes once a frame after a vertical-blank wait. Reports fps
                          and fields a frame (p50, p95, max, histogram)
    aprof N OUT [SCRIPT]  the same with an aprof capture of every field (FSUAE=$FSUAE_APROF):
                          OUT.json holds each field's time by category (CATEGORIES), whether
                          drawPt swapped, and the time per game offset; tools/frametime.py
                          reports it
    play SCRIPT           run an input script: steps separated by ';', each
                          `F [mx MX] [my MY] [fire]`: F fields with the mouse moved MX, MY a
                          field (forward is my -N) and the button held; or a name from
                          SCRIPTS (`play walk`, the baseline's scripted walk)
    batch CMD ;; CMD      gdb commands in one request, CPU stopped

The 8-channel ($c4dc) version only, which the AGA drawer installs.
"""
import re
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
PLR1MOUSE = 0x5d82      # nonzero with mouse control (M; Plr1Control's key test at $401ee)
KEY_RETURN, KEY_M, KEY_ENTER = 0x44, 0x37, 0x43


def _bytes(g, addr, n):
    out = g.cmd(f'x/{n}xb {addr:#x}')
    vals = []
    for line in out.splitlines():
        # only the dump's own lines: a 68040 stop can add MMU state lines (TC=8000 ...)
        if re.match(r'^0x[0-9a-f]+(\s*<[^>]*>)?:', line):
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
    drawPt swaps; then M until PLR1MOUSE is set."""
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
        # M until PLR1MOUSE is set: the level's start can clear it after the first frames
        for m in range(1, 11):
            g.cmd('monitor fields 40')
            _key(g, KEY_M)
            if _bytes(g, addr(g, PLR1MOUSE), 1)[0]:
                break
        else:
            raise RuntimeError('M did not select mouse control')
        return (f'in level 1 after {n + 10} fields and {presses} RETURNs; mouse control on '
                f'after {m} M')


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


# Named input scripts for repeatable scenes (game time follows the frame rate, so a script
# ends in the same place only on the same machine).
SCRIPTS = {
    # level 1: down the start corridor, through the door, round the room, back out
    'walk': '200 my -10; 50 mx 20; 100 my -10; 50 mx -20; 100 my -10; 50 mx 30',
}


def script_fields(text):
    """A script as one (mx, my, fire) per field."""
    text = SCRIPTS.get(text.strip(), text)
    out = []
    for step in filter(None, (s.strip() for s in text.split(';'))):
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
        out += [(mx, my, fire)] * fields
    return out


def run_fields(g, n, inputs=(), after=None):
    """Run n fields one at a time, feeding inputs[i] before field i (none past its end), and
    call after(i) once each field has run. Releases the button at the end."""
    held = False
    for i in range(n):
        mx, my, fire = inputs[i] if i < len(inputs) else (0, 0, False)
        if fire != held:
            g.cmd(f'monitor input JOY1_FIRE_BUTTON {int(fire)}')
            held = fire
        if mx or my:
            g.cmd(f'monitor mouse {mx} {my}')
        g.cmd('monitor fields 1')
        if after:
            after(i)
    if held:
        g.cmd('monitor input JOY1_FIRE_BUTTON 0')


def _split(rest, n_default):
    """'N [SCRIPT]' -> (N, inputs)."""
    w = rest.strip().split(None, 1)
    n = int(w[0]) if w else n_default
    return n, script_fields(w[1]) if len(w) > 1 else []


def cmd_frames(server, g, rest):
    n, inputs = _split(rest, 500)
    with Halted(g):
        a = addr(g, DRAWPT)
        st = {'last': _long(g, a), 'at': None}
        gaps = []

        def after(i):
            p = _long(g, a)
            if p != st['last']:
                if st['at'] is not None:
                    gaps.append(i - st['at'])
                st['at'], st['last'] = i, p
        run_fields(g, n, inputs, after)
    if not gaps:
        return f'{n} fields: no complete frame'
    frames = len(gaps)
    mean = sum(gaps) / frames
    hist = ' '.join(f'{k}:{gaps.count(k)}' for k in sorted(set(gaps)))
    return (f'{n} fields: {frames} whole frames, {50 / mean:.2f} fps; fields a frame mean '
            f'{mean:.2f} p50 {_percentile(gaps, .5)} p95 {_percentile(gaps, .95)} max {max(gaps)}'
            f'; histogram {hist}')


def cmd_play(server, g, rest):
    inputs = script_fields(rest)
    with Halted(g):
        run_fields(g, len(inputs), inputs)
    return f'played {len(inputs)} fields'


# Where the time goes, by game offset (docs/performance.md; the routines are tools/srcmatch.py's).
CATEGORIES = [
    # the frame waits: INTREQR bit 0, which the copper list sets at the top of the field
    # ($9a084) and clears at line $10 ($9a24c); $32fe is the single-player loop's
    ('wait', [(0x32fe, 0x3306), (0x8e9e, 0x8ea8), (0x8efa, 0x8f04)]),
    ('gun', [(0x57f4, 0x58da)]),
    ('geometry', [(0x6538, 0x8364), (0x8458, 0x88d6), (0x8a16, 0x8bea), (0x93c2, 0x95e4)]),
    # the sky: putinbackdrop, and the unrolled writer MAKEBACKROUT copies into backrout
    ('backdrop', [(0x18ffa, 0x1947e)]),
    ('walls', [(0x19af4, 0x1d27a)]),
    ('floors', [(0x1d27a, 0x1fce2), (0x20f4c, 0x21160)]),
    ('bump', [(0x1fce2, 0x20f4c)]),
    ('objects', [(0x21160, 0x3fefa)]),
    ('interrupts', [(0x3fefa, 0x3ff5a), (0x415d8, 0x41800), (0x9b2dc, 0xad9e8)]),
]
WAITVBL_CALL = 0x3e58   # the main loop's jsr to the slave's _waitvbl (PL_PS)


def _layout(g):
    """Hunk bases and the slave's _waitvbl (26 bytes; another loop's frame wait), from the
    jsr the slave patched in."""
    call = _bytes(g, addr(g, WAITVBL_CALL), 6)
    if call[:2] != b'\x4e\xb9':
        raise RuntimeError(f'no jsr at ${WAITVBL_CALL:x}: {call.hex()}')
    return {'hunks': bases(g), 'waitvbl': struct.unpack('>I', call[2:])[0]}


def classifier(layout):
    """pc -> (category, game offset or None)."""
    spans, start = [], 0
    for size, base in zip(HUNKS, layout['hunks']):
        spans.append((base, base + size, start))
        start += size
    w = layout['waitvbl']

    def classify(pc):
        if w <= pc < w + 26:
            return 'wait', None
        for lo, hi, off in spans:
            if lo <= pc < hi:
                o = pc - lo + off
                for name, ranges in CATEGORIES:
                    if any(a <= o < b for a, b in ranges):
                        return name, o
                return 'logic', o
        return ('rom' if pc >= 0xf80000 and pc < 0x1000000 else 'slave'), None
    return classify


def _parse(parse_profile, text):
    """amigaxdev.aprof.parse_profile's header and PCs. Its stop-tail bound (one colour clock)
    fails on the 14 MHz 68020, where the instruction running at the stop can take several:
    for that case alone the PC/tree accounting is checked here and the tail kept, which
    frametime.py reports."""
    try:
        h, p, _ = parse_profile(text)
        return h, p
    except ValueError as e:
        if 'UNBOUNDED PROFILE TAIL' not in str(e):
            raise
    h, p, nodes = {}, {}, 0
    for line in text.splitlines()[1:]:
        f = line.split()
        if f and f[0] == 'P':
            p[int(f[1], 16)] = (int(f[2]), int(f[3]), int(f[4]), int(f[5]))
        elif f and f[0] == 'N':
            nodes += int(f[5])
        elif len(f) == 2:
            h[f[0]] = int(f[1], 16) if f[0] == 'cacr' else (int(f[1]) if f[1].lstrip('-').isdigit() else f[1])
    if sum(v[0] for v in p.values()) + h['gap'] + h.get('high', 0) != nodes or h['overflow']:
        raise ValueError('APROF / PC/TREE ACCOUNTING (with an unbounded tail)')
    h['tail'] = h['units'] - nodes
    if not 0 <= h['tail'] < 16 * h['CYCLE_UNIT']:
        raise ValueError(f"APROF / tail {h['tail']} units")
    return h, p


def cmd_aprof(server, g, rest):
    """aprof N OUT.json [SCRIPT]: an aprof capture of each of N fields (FSUAE_APROF only)."""
    import json
    sys.path.insert(0, str(Path.home() / '.local/share/amiga/pylib'))
    from amigaxdev.aprof import parse_profile
    w = rest.split(None, 2)
    n, out = int(w[0]), Path(w[1]).resolve()
    inputs = script_fields(w[2]) if len(w) > 2 else []
    prof = out.with_suffix('.prof')
    fields, pcs = [], {}
    with Halted(g):
        lay = _layout(g)
        classify = classifier(lay)
        a = addr(g, DRAWPT)
        st = {'last': _long(g, a)}
        g.cmd('monitor aprof start')

        def after(i):
            r = g.cmd(f'monitor aprof stop {prof}', timeout=120)
            g.cmd('monitor aprof start')
            h, p = _parse(parse_profile, prof.read_text())
            cats, execs_by = {}, {}
            for pc, (units, execs, chip, _n) in p.items():
                c, off = classify(pc)
                cats[c] = cats.get(c, 0) + units
                execs_by[c] = execs_by.get(c, 0) + execs
                if off is not None:
                    t = pcs.setdefault(off, [0, 0, 0, c])
                    t[0] += units
                    t[1] += execs
                    t[2] += chip
            d = _long(g, a)
            fields.append({'units': h['units'], 'gap': h['gap'], 'high': h.get('high', 0),
                           'tail': h['tail'], 'chip': h['chip_units'], 'cats': cats, 'execs': execs_by,
                           'swap': d != st['last'], 'vsyncs': h['vsyncs']})
            st['last'] = d
            st['header'] = h
        run_fields(g, n, inputs, after)
        g.cmd(f'monitor aprof stop {prof}', timeout=120)
        prof.unlink(missing_ok=True)
    h = st['header']
    meta = {k: h[k] for k in ('cycleunit', 'CYCLE_UNIT', 'colorclock_hz', 'cpu_model', 'cacr')}
    out.write_text(json.dumps({'meta': meta, 'layout': lay, 'fields': fields,
                               'pcs': {f'{k:x}': v for k, v in sorted(pcs.items())}}))
    return f'{n} fields captured into {out} ({sum(f["swap"] for f in fields)} swaps)'


def cmd_batch(server, g, rest):
    with Halted(g):
        return ''.join(g.cmd(c, timeout=600).rstrip('\n') + '\n'
                       for c in rest.split(' ;; ') if c.strip())


server = game_server('ab3d', commands={
    'base': cmd_base, 'peek': cmd_peek, 'level': cmd_level, 'full': cmd_full,
    'frames': cmd_frames, 'play': cmd_play, 'aprof': cmd_aprof, 'batch': cmd_batch})

if __name__ == '__main__':
    server.main(sys.argv[1:])
