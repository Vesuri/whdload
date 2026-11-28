"""Alien Breed 3D gdb-stub server: the shared commands (common/tools/game_server.py) and these.

    INSTANCE=x WARP=1 WINDOW=none python3 tools/ab3d.py serve &   boot (common/run.sh options)
    python3 tools/ab3d.py CMD ...                                  one command to the server

Game commands (game offsets as in docs/internals.md, $c4dc version, which with the CD32
version ($fd78) are mapped to its own by tools/port.py; the CPU is left as it was found,
running or stopped):
    base                  where the hunks are: hunk 0 and the chip hunks' runtime addresses
    peek OFF [N]          N bytes (default 4) at game offset OFF, hex
    level                 from the main menu into the level: once no frame has been drawn for
                          50 fields (a death's or a level end's last frames), RETURN every
                          100 fields until the first frames, then M until mouse control is
                          on (PLR1MOUSE)
    next                  F1 (WHD_ARGS=CUSTOM1=4: F1 skips the level), then into the next
                          level the same way
    end                   F1 (WHD_ARGS=CUSTOM1=4) and run until the level's last frame stays
                          (no frame for twice its longest frame, at least 8 fields)
    full [0|1]            the view: print it, or press keypad Enter until it is the one asked
                          (0 small, 1 full screen)
    frames [N [SCRIPT]]   run N fields (default 500) one at a time, playing SCRIPT, and count
                          the frames shown: swaps of drawPt (offset $5dd40), which the main
                          loop makes once a frame after a vertical-blank wait. Reports fps
                          and fields a frame (p50, p95, max, histogram). N `turn`: hold
                          the right arrow until the view has turned a full circle (angle
                          at $61d78; keyboard control, `key 27`, K)
    aprof N OUT [SCRIPT]  the same with an aprof capture of every field (FSUAE=$FSUAE_APROF):
                          OUT.json holds each field's time by category (CATEGORIES), whether
                          drawPt swapped, and the time per game offset; tools/frametime.py
                          reports it
    pos                   player 1's x, z and view angle
    play SCRIPT           run an input script: steps separated by ';', each
                          `F [mx MX] [my MY] [fire] [key CODE]`: F fields with the mouse
                          moved MX, MY a field (forward is my -N), the button held and raw
                          key CODE (hex) held; or a name from SCRIPTS (`play walk`, the
                          baseline's scripted walk)
    copper [WHAT]         decode a live copper list: `template` (default, game offset
                          $9a07c, the field's start to the jump into the view), `panel`
                          ($9a262, the panel split) or `view [LINE]` (line LINE of the list
                          drawPt points at, default 0). Runs of COLOR moves are one line each,
                          with the bank and LOCT that BPLCON3 selected
    batch CMD ;; CMD      gdb commands in one request, CPU stopped
    grab N OUT [SCRIPT]   run N fields playing SCRIPT and append each frame shown to OUT:
                          96x80 big-endian 12-bit colour words, read from the view list
    holes N OUT [SCRIPT]  with a HOLES build (VASM_EXTRA=-DHOLES: the list drawn next is $f0f
                          in every pixel; in pen lists pen 1, read as $f0f): N fields playing SCRIPT, and in each frame shown
                          (its size from the slave's DA_INFO) the pixels no writer drew but
                          on line 0, which none draws in the original either. The
                          frame with the most goes to OUT (as `frame`'s, no .alt)
    tables DIR            the loaded walls (DIR/wallNN: shade table, then texels) and the
                          floor texture (DIR/floortile), which tools/colours.py reads
    pause on|off          press P until the game is paused or playing again (the byte
                          at $8e18, which the main loop clears at P), at most 3 times
    key CODE [N]          press raw key CODE (hex; P, 19, pauses) for N fields (default 10),
                          then release it for N
    chunky OUT            the pens of the frame last shown (CUSTOM5=1: the list itself, or a
                          WORDS build's chunky buffer): width, height (words), then W x H bytes
    frame OUT             the frame on screen (oldDrawPt) into OUT: its colour words (a pen
                          list's pens through the area's palette), the
                          view byte (0 small, 1 full screen), width and height (words;
                          96x80, or with CUSTOM5=1 the slave's DA_INFO); drawPt's into OUT.alt
                          when it holds a view too (the game swaps the pointers a little
                          before it shows the list, so either may be on screen)
    die N [SCRIPT]        play SCRIPT (default `fight`) for up to N fields until player 1's
                          energy ($61d70) is 0 or less: the death's last frame then shows
    palette OUT [N]       from the boot (WHD_ARGS=CUSTOM5=1), field by field for up to N
                          (default 3000): wait for the slave's palette build (src/palette.s)
                          to finish, print the fields it took (each step's, from the state
                          word) and dump its area to OUT, which
                          `tools/colours.py check OUT` compares with the model. The dump
                          reads memory: on a 68040 dump again after some play (N=1), as
                          copyback can still hold the build's last writes

The 8-channel ($c4dc) version, which the AGA drawer installs, and the CD32 one ($fd78, the
CD32 drawer: GAME_DIR=AlienBreed3DCD32 SLAVE_FILE=AlienBreed3DCD32.slave); `aprof`'s
categories, `tables` and `copper template`'s decoding are the $c4dc version's only.
"""
import os
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

FLAT = Path(__file__).resolve().parents[1] / 'tmp/exe/abd.flat'
# hunk sizes of the $c4dc version (tools/exe.py): code and data, then three chip hunks; the
# CD32 one's ($fd78), whose offsets addr() maps from the $c4dc ones (tools/port.py)
HUNKS = (0x912d4, 0x9f64, 0x18, 0x12798)
HUNKS_CD32 = (0x93654, 0x9f64, 0x18, 0x12798, 0x17fc)
DRAWPT = 0x5dd40        # drawPt, the copper list being drawn; oldDrawPt follows
FULL = 0x40279          # nonzero in full screen (flipped by keypad Enter)
PLR1MOUSE = 0x5d82      # nonzero with mouse control (M; Plr1Control's key test at $401ee)
KEY_RETURN, KEY_M, KEY_ENTER, KEY_F1, KEY_P = 0x44, 0x37, 0x43, 0x50, 0x19
ENERGY = 0x61d70        # player 1's energy (word); quitGame copies it to $8bfa
LEVEL_LETTER = 0x2a29   # the level's letter in 'ab3d2:levels/level_a/twolev.bin', set per level
# what the colour census reads (tools/colours.py; all loaded once, before the menu)
WALLTILES = 0x42a66     # walltiles: a pointer to each loaded wall file (LoadWalls)
WALLCHUNKDATA = 0x42b06  # wallchunkdata: (name, unpacked size) pairs, ended by zeros
FLOORTILE = 0x55cee     # floortile: a pointer to the loaded floor texture
FLOORTILE_SIZE = 65536
# Enhanced resolution's area (src/palette.s): from ExpMem, the bytes that stay, the state word
PALETTE_AREA, PALETTE_END, PALETTE_STATE = 0x158000, 58080, 2


def _bytes(g, addr, n):
    out = g.cmd(f'x/{n}xb {addr:#x}')
    if 'Cannot access memory' in out:
        raise RuntimeError(f'cannot read {addr:#x}')
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


def layout(g):
    """The version's hunk sizes and the runtime address of each hunk's data. The slave
    relocates the game in LoadSeg layout (each hunk: its allocation size, then the link, a
    BPTR to the next hunk's link, then the data) at ExpMem+$2000, $3000 further on when
    HackAB3D is loaded before it; the fake ExecBase is ExpMem+$1000. The hunk sizes tell the
    version."""
    key = _long(g, 4)
    if key in _bases:
        return _bases[key]
    expmem = key - 0x1000
    for hunks in (HUNKS, HUNKS_CD32):
        for seg in (expmem + 0x2000 + 0x3000, expmem + 0x2000):
            out, link = [], seg + 4
            for size in hunks:
                if not link or _long(g, link - 4) != size + 8:
                    break
                out.append(link + 4)
                link = _long(g, link) * 4
            if len(out) == len(hunks):
                _bases[key] = hunks, out
                return hunks, out
    raise RuntimeError(f'game hunks not found from ExecBase {key:#x}: not loaded yet, or '
                       'not the $c4dc or CD32 version')


def bases(g):
    return layout(g)[1]


def cd32(g):
    return layout(g)[0] == HUNKS_CD32


_ported = {}


def addr(g, off):
    """Game offset ($c4dc) to runtime address; with the CD32 version, its offset's."""
    hunks, b = layout(g)
    if hunks == HUNKS_CD32:
        if off not in _ported:
            import port
            _ported[off] = port.port(off)[0]
        off = _ported[off]
    start = 0
    for size, base in zip(hunks, b):
        if off < start + size:
            return base + off - start
        start += size
    raise ValueError(f'offset {off:#x} past the last hunk')


def cmd_base(server, g, rest):
    with Halted(g):
        hunks, b = layout(g)
        start, lines = 0, ['the CD32 version ($fd78; offsets mapped from $c4dc)'
                           if hunks == HUNKS_CD32 else 'the $c4dc version']
        for i, (size, a) in enumerate(zip(hunks, b)):
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


def _swapped(g, first, fields):
    """Run up to `fields` fields one at a time; True once drawPt is not `first`."""
    for _ in range(fields):
        g.cmd('monitor fields 1')
        if _drawpt(g) != first:
            return True
    return False


def _press(g, code, limit=200):
    """Press and release a key the game reads once a frame: held until two frames are
    shown (at least 10 fields; a 14 MHz 68020's full-screen frame is 13 or more), released
    until one more is shown, waiting up to `limit` fields for each frame (F1 ends the
    level: no more frames)."""
    g.cmd(f'monitor key {code:x} 1')
    g.cmd('monitor fields 10')
    for _ in range(2):
        if not _swapped(g, _drawpt(g), limit):
            break
    g.cmd(f'monitor key {code:x} 0')
    g.cmd('monitor fields 10')
    _swapped(g, _drawpt(g), limit)


def _letter(g):
    return chr(_bytes(g, addr(g, LEVEL_LETTER), 1)[0])


def _quiet(g, fields, limit):
    """Run until drawPt has not swapped for `fields` fields; the fields run, or None after
    `limit`."""
    last, still = _drawpt(g), 0
    for n in range(1, limit + 1):
        g.cmd('monitor fields 1')
        d = _drawpt(g)
        still = still + 1 if d == last else 0
        last = d
        if still >= fields:
            return n
    return None


def _enter_level(g):
    """Wait until no frame is drawn (a death's or a level end's frames can still swap),
    then RETURN every 100 fields (the menu, then the text screen once it has loaded) until
    drawPt swaps; then M until PLR1MOUSE is set."""
    if _quiet(g, 50, 3000) is None:
        raise RuntimeError('frames still drawn after 3000 fields')
    first, presses = _drawpt(g), 0
    for n in range(0, 4000, 10):
        if n % 100 == 0:
            _key(g, KEY_RETURN)
            presses += 1
        # field by field: 10 fields can hold an even number of swaps; a death's last
        # frames (energy 0 or less) are not the level's
        if _swapped(g, first, 10):
            if struct.unpack('>h', _bytes(g, addr(g, ENERGY), 2))[0] > 0:
                break
            first = _drawpt(g)
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
    return (f'in level {_letter(g).upper()} after {n + 10} fields and {presses} RETURNs; '
            f'mouse control on after {m} M')


def cmd_level(server, g, rest):
    with Halted(g):
        return _enter_level(g)


def cmd_next(server, g, rest):
    """F1 (with CUSTOM1 bit 2) ends the level; wait for the next one's name, then enter it."""
    with Halted(g):
        was = _letter(g)
        _press(g, KEY_F1, 40)
        for n in range(0, 6000, 10):
            if n % 100 == 50:
                _key(g, KEY_RETURN)
            g.cmd('monitor fields 10')
            if _letter(g) != was:
                break
        else:
            raise RuntimeError(f'level {was.upper()} did not end within 6000 fields of F1 '
                               '(CUSTOM1=4 in WHD_ARGS?)')
        return _enter_level(g)


def cmd_end(server, g, rest):
    """F1 (with CUSTOM1 bit 2) ends the level; run until its last frame stays: no swap for
    twice the longest frame of the 60 fields before (at least 8 fields). No longer: the
    no-music slave plays no tune over it, so soon after the screen fades to the menu."""
    with Halted(g):
        was = _letter(g)
        last, gap, longest = _drawpt(g), 0, 0
        for _ in range(60):
            g.cmd('monitor fields 1')
            d = _drawpt(g)
            gap = gap + 1 if d == last else 0
            longest = max(longest, gap + 1)
            last = d
        _press(g, KEY_F1, 40)
        n = _quiet(g, max(8, 2 * longest), 1000)
        if n is None:
            raise RuntimeError('frames still drawn 1000 fields after F1 (CUSTOM1=4 in WHD_ARGS?)')
        if _letter(g) != was:
            raise RuntimeError('the next level loaded before the last frame was seen')
        return f'level {was.upper()} ended, its last frame still after {n + 20} fields'


def cmd_full(server, g, rest):
    with Halted(g):
        def state():
            return _bytes(g, addr(g, FULL), 1)[0] != 0
        if rest.strip():
            want = rest.strip() == '1'
            for _ in range(3):
                if state() == want:
                    break
                _press(g, KEY_ENTER)
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
    # tools/census.sh's: turning and walking with the gun firing
    'fight': '60 mx 40 fire; 120 my -12 fire; 60 mx -40 fire; 120 my -12 fire; '
             '60 mx 40 fire; 120 my -12 fire; 60 mx 40 fire; 120 my -12 fire',
    # level 1 with keyboard control (K): to the middle of the start room (tools/turn.sh)
    'centre': '30 key 4c',
    # level 1 from its start (mouse control): to the first door, Space while walking into it
    # (a door opens on a tap in a frame the player touches its wall), into the dark room
    # with the aliens, to its middle (x -720, z 1870)
    'door': '300 my -10; 20 my -6 key 40; 50; 35 my -10; 15',
    # there: two full turns firing (the barrels explode, the aliens take hits), then firing
    'turn720': '210 mx 20 fire; 40 fire',
}
KEY_K, KEY_UP, KEY_RIGHT = 0x27, 0x4c, 0x4e
ANGLE = 0x61d78         # player 1's view angle (word, 0-8191 a full circle; right adds)
TURN_MAX = 4000         # `turn`'s limit, in fields


def script_fields(text):
    """A script as one (mx, my, fire, key) per field."""
    text = SCRIPTS.get(text.strip(), text)
    out = []
    for step in filter(None, (s.strip() for s in text.split(';'))):
        w = step.split()
        fields, mx, my, fire, key = int(w[0]), 0, 0, False, None
        i = 1
        while i < len(w):
            if w[i] == 'mx':
                mx, i = int(w[i + 1]), i + 2
            elif w[i] == 'my':
                my, i = int(w[i + 1]), i + 2
            elif w[i] == 'fire':
                fire, i = True, i + 1
            elif w[i] == 'key':
                key, i = int(w[i + 1], 16), i + 2
            else:
                raise ValueError(f'unknown word {w[i]!r} in {step!r}')
        out += [(mx, my, fire, key)] * fields
    return out


def run_fields(g, n, inputs=(), after=None, until=None):
    """Run n fields one at a time, feeding inputs[i] before field i (none past its end), and
    call after(i) once each field has run; stop early once until() is true. Releases the
    button and the key at the end. Returns the fields run."""
    held, down, i = False, None, -1
    for i in range(n):
        mx, my, fire, key = inputs[i] if i < len(inputs) else (0, 0, False, None)
        if fire != held:
            g.cmd(f'monitor input JOY1_FIRE_BUTTON {int(fire)}')
            held = fire
        if key != down:
            if down is not None:
                g.cmd(f'monitor key {down:x} 0')
            if key is not None:
                g.cmd(f'monitor key {key:x} 1')
            down = key
        if mx or my:
            g.cmd(f'monitor mouse {mx} {my}')
        g.cmd('monitor fields 1')
        if after:
            after(i)
        if until and until():
            break
    if held:
        g.cmd('monitor input JOY1_FIRE_BUTTON 0')
    if down is not None:
        g.cmd(f'monitor key {down:x} 0')
    return i + 1


def _turn(g, text):
    """'N [SCRIPT]', or `turn`: the right arrow held until the angle has gone a full circle
    (keyboard control, K; at most TURN_MAX fields). (n, inputs, until)."""
    w = text.strip().split(None, 1)
    if not w or w[0] != 'turn':
        n = int(w[0]) if w else 500
        return n, script_fields(w[1]) if len(w) > 1 else [], None
    a = addr(g, ANGLE)
    st = {'last': _angle(g, a), 'gone': 0}

    def until():
        now = _angle(g, a)
        st['gone'] += (now - st['last']) & 8191
        st['last'] = now
        return st['gone'] >= 8192
    return TURN_MAX, script_fields(f'{TURN_MAX} key {KEY_RIGHT:x}'), until


def _angle(g, a):
    return struct.unpack('>H', _bytes(g, a, 2))[0] & 8191


def cmd_frames(server, g, rest):
    with Halted(g):
        n, inputs, until = _turn(g, rest)
        a = addr(g, DRAWPT)
        st = {'last': _long(g, a), 'at': None}
        gaps = []

        def after(i):
            p = _long(g, a)
            if p != st['last']:
                if st['at'] is not None:
                    gaps.append(i - st['at'])
                st['at'], st['last'] = i, p
        n = run_fields(g, n, inputs, after, until)
    if until and n == TURN_MAX:
        raise RuntimeError(f'no full turn in {n} fields (keyboard control, K?)')
    if not gaps:
        return f'{n} fields: no complete frame'
    frames = len(gaps)
    mean = sum(gaps) / frames
    hist = ' '.join(f'{k}:{gaps.count(k)}' for k in sorted(set(gaps)))
    return (f'{n} fields: {frames} whole frames, {50 / mean:.2f} fps; fields a frame mean '
            f'{mean:.2f} p50 {_percentile(gaps, .5)} p95 {_percentile(gaps, .95)} max {max(gaps)}'
            f'; histogram {hist}')


def _dump(g, a, n, path):
    """n bytes from runtime address a, through gdb's dump into path (x/xb is far slower)."""
    g.cmd(f'dump binary memory {path} {a:#x} {a + n:#x}', timeout=300)
    data = Path(path).read_bytes()
    if len(data) != n:
        raise RuntimeError(f'dump of {n} bytes at {a:#x} gave {len(data)}')
    return data


VIEW_W, VIEW_H = 96, 80
# Enhanced resolution's lists (src/display.s): the same slot layout, lines of DS_STRIDE
# bytes, and the frame's size in the area's DA_INFO (stride, width, height words; then
# where its pens are, a long, and their line stride, a word)
DA_CHUNKY = 58080                       # PA_END: the pens the c2p reads, W x H
DA_INFO = DA_CHUNKY + 288 * 240 + 16 + 144


def geometry(g):
    """(stride, width, height, palette) of the frame in the lists: the original's 416, 96, 80
    and None, or with WHD_ARGS CUSTOM5=1 what the slave last showed; palette is None when the
    lists hold colour words (a WORDS or LORES build), else each pen's colour word (the
    writers write pens, which the c2p reads from the list itself)."""
    if 'CUSTOM5=1' not in os.environ.get('WHD_ARGS', ''):
        return VIEW_LINE, VIEW_W, VIEW_H, None
    area = _long(g, 4) - 0x1000 + PALETTE_AREA
    stride, w, h, pens = struct.unpack('>HHHI', _bytes(g, area + DA_INFO, 10))
    if pens == area + DA_CHUNKY:
        return stride, w, h, None
    n = struct.unpack('>H', _bytes(g, area, 2))[0]          # PA_NPENS
    cols = struct.unpack(f'>{n}H', _bytes(g, area + 4, 2 * n))
    # pens 0-15 are no writer's: 0 is line 0's black, 1 a HOLES build's hole
    return stride, w, h, [0, 0x0f0f] + [0] * (PEN0 - 2) + list(cols) + [0] * (256 - PEN0 - n)


PEN0 = 16


def list_words(g, at, geom, scratch):
    """The frame in the list at runtime address at as colour words (view_words'), from
    either kind of list."""
    stride, w, h, pal = geom
    if pal is None:
        return view_words(_dump(g, at, stride * h + 16, scratch), geom[:3])
    raw = _dump(g, at + 10, stride * h, scratch)
    return b''.join(struct.pack(f'>{w}H', *(pal[p] for p in raw[y * stride:y * stride + w]))
                    for y in range(h))


def view_words(raw, geom=None):
    """A view list's colour words (big-endian, row by row): pixel x of a line is the data
    word of COLOR move x % 32 in bank x // 32 (fromPt is the list + 10). The original's
    lists are checked to hold COLOR moves there; ours are never shown as copper lists."""
    stride, w, h = geom or (VIEW_LINE, VIEW_W, VIEW_H)
    out = bytearray()
    for y in range(h):
        line = raw[y * stride:y * stride + 12 + (w - 1) // 32 * 132 + (w - 1) % 32 * 4]
        for x in range(w):
            o = 8 + (x // 32) * 132 + (x % 32) * 4
            if stride == VIEW_LINE and struct.unpack_from('>H', line, o)[0] != 0x180 + 2 * (x % 32):
                raise RuntimeError(f'line {y} pixel {x}: not a COLOR move')
            out += line[o + 2:o + 4]
    return bytes(out)


def cmd_grab(server, g, rest):
    """grab N OUT [SCRIPT]: N fields playing SCRIPT; append each frame shown (oldDrawPt after
    a swap) to OUT as 96x80 big-endian colour words."""
    w = rest.split(None, 2)
    n, out = int(w[0]), Path(w[1]).resolve()
    inputs = script_fields(w[2]) if len(w) > 2 else []
    scratch = out.with_name(out.name + '.list')
    with Halted(g):
        a = addr(g, DRAWPT)
        st = {'last': _long(g, a), 'frames': 0}
        with open(out, 'ab') as fo:
            def after(i):
                p = _long(g, a)
                if p != st['last']:
                    st['last'] = p
                    fo.write(view_words(_dump(g, _long(g, a + 4), VIEW_H * VIEW_LINE, scratch)))
                    st['frames'] += 1
            run_fields(g, n, inputs, after)
        scratch.unlink(missing_ok=True)
        return f'level {_letter(g).upper()}: {st["frames"]} frames into {out}'


def cmd_holes(server, g, rest):
    w = rest.split(None, 2)
    n, out = int(w[0]), Path(w[1]).resolve()
    inputs = script_fields(w[2]) if len(w) > 2 else []
    scratch = out.with_name(out.name + '.list')
    with Halted(g):
        a = addr(g, DRAWPT)
        st = {'last': _long(g, a), 'frames': 0, 'holed': 0, 'most': -1, 'total': 0}
        def after(i):
            p = _long(g, a)
            if p == st['last']:
                return
            st['last'] = p
            geom = geometry(g)
            words = list_words(g, _long(g, a + 4), geom, scratch)
            # not line 0: no writer draws it, in the original either (display.s _ds_one)
            k = sum(1 for (v,) in struct.iter_unpack('>H', words[2 * geom[1]:]) if v == 0x0f0f)
            st['frames'] += 1
            st['total'] += k
            if k:
                st['holed'] += 1
            if k > st['most']:
                st['most'] = k
                full = _bytes(g, addr(g, FULL), 1)[0] != 0
                out.write_bytes(words + bytes([full]) + struct.pack('>HH', geom[1], geom[2]))
                st['at'] = (i, geom[1], geom[2])
        run_fields(g, n, inputs, after)
        scratch.unlink(missing_ok=True)
        return (f'level {_letter(g).upper()}: {st["frames"]} frames, {st["holed"]} with holes, '
                f'{st["total"]} hole pixels; the most, {st["most"]}, at field {st["at"][0]} '
                f'({st["at"][1]}x{st["at"][2]}) into {out}')


def cmd_chunky(server, g, rest):
    """chunky OUT: the pens of the frame last shown (WHD_ARGS=CUSTOM5=1), which the c2p
    reads: where DA_INFO says (DI_PENS, DI_PROW: the slave's chunky buffer, or with PENS the
    list itself). OUT is its width and height (big-endian words), then the pens row by
    row."""
    out = Path(rest.strip()).resolve()
    with Halted(g):
        area = _long(g, 4) - 0x1000 + PALETTE_AREA
        _, w, h, pens, row = struct.unpack('>HHHIH', _bytes(g, area + DA_INFO, 12))
        raw = _dump(g, pens, row * h, out.with_suffix('.tmp'))
    out.with_suffix('.tmp').unlink()
    out.write_bytes(struct.pack('>HH', w, h) + b''.join(raw[y * row:y * row + w] for y in range(h)))
    return f'{w}x{h} pens into {out}'


def cmd_frame(server, g, rest):
    out = Path(rest.strip()).resolve()
    with Halted(g):
        lists = []
        geom = geometry(g)
        for at in (4, 0):           # oldDrawPt, the one shown, then drawPt
            try:
                lists.append(list_words(g, _long(g, addr(g, DRAWPT) + at), geom,
                                        out.with_name(out.name + '.list')))
            except RuntimeError:
                lists.append(None)
        full = _bytes(g, addr(g, FULL), 1)[0] != 0
    out.with_name(out.name + '.list').unlink(missing_ok=True)
    alt = out.with_name(out.name + '.alt')
    alt.unlink(missing_ok=True)
    if lists[0] is None and lists[1] is None:
        raise RuntimeError('neither list holds a view')
    if lists[0] is None:
        lists = lists[1:]
    tail = bytes([full]) + struct.pack('>HH', geom[1], geom[2])
    out.write_bytes(lists[0] + tail)
    if len(lists) > 1 and lists[1] is not None:
        alt.write_bytes(lists[1] + tail)
    return (f'the frame on screen ({"full screen" if full else "small view"}, '
            f'{geom[1]}x{geom[2]}) into {out}')


PLAYING = 0x8e18         # byte: 0 from the main loop's P (it waits for the release) until
                         # the pause loop ($3e64) returns, else $ff


def cmd_pause(server, g, rest):
    """P until the game is paused (`on`) or playing again (`off`), read from PLAYING. The
    main loop reads P once a frame (13 fields or more on a 14 MHz 68020 in full screen),
    so `on` holds it until the game has seen it; the pause loop polls it all the time."""
    on = rest.strip() != 'off'
    with Halted(g):
        a = addr(g, PLAYING)

        def playing():
            return _bytes(g, a, 1)[0] != 0
        if playing() != on:
            return 'paused' if on else 'playing'
        for tries in range(1, 4):
            g.cmd(f'monitor key {KEY_P:x} 1')
            for n in range(400 if on else 10):
                g.cmd('monitor fields 1')
                if on and not playing():
                    break
            g.cmd(f'monitor key {KEY_P:x} 0')
            for n in range(1, 401):
                g.cmd('monitor fields 1')
                if playing() != on:
                    break
            if playing() != on:
                g.cmd('monitor fields 60')     # the pause screen drawn, or a frame again
                return f'{"paused" if on else "playing"} after {tries} P'
    raise RuntimeError(f'not {"paused" if on else "playing"} after 3 P')


def cmd_key(server, g, rest):
    w = rest.split()
    with Halted(g):
        _key(g, int(w[0], 16), int(w[1]) if len(w) > 1 else 10)
    return f'key {w[0]}'


def cmd_die(server, g, rest):
    w = rest.split(None, 1)
    n = int(w[0])
    inputs = script_fields(w[1] if len(w) > 1 else 'fight')
    inputs = (inputs * (n // len(inputs) + 1))[:n]

    class Dead(Exception):
        pass

    with Halted(g):
        a = addr(g, ENERGY)

        def after(i):
            if struct.unpack('>h', _bytes(g, a, 2))[0] <= 0:
                raise Dead(i + 1)
        try:
            run_fields(g, n, inputs, after)
        except Dead as e:
            g.cmd('monitor input JOY1_FIRE_BUTTON 0')
            return f'energy 0 after {e.args[0]} fields'
    raise RuntimeError(f'still alive after {n} fields')


def cmd_tables(server, g, rest):
    """tables DIR: the loaded walls (DIR/wallNN, each its 2048-byte shade table then texels)
    and the floor texture (DIR/floortile), for tools/colours.py."""
    d = Path(rest.strip()).resolve()
    d.mkdir(parents=True, exist_ok=True)
    with Halted(g):
        names = []
        for i in range(40):
            size = _long(g, addr(g, WALLCHUNKDATA + 8 * i + 4))
            if not size:
                break
            _dump(g, _long(g, addr(g, WALLTILES + 4 * i)), size, d / f'wall{i:02d}')
            names.append(f'wall{i:02d} {size}')
        _dump(g, _long(g, addr(g, FLOORTILE)), FLOORTILE_SIZE, d / 'floortile')
    return f'{len(names)} walls and the floor texture into {d}'


def cmd_palette(server, g, rest):
    """palette OUT [N]: the slave's palette build, timed in fields, and its area dumped."""
    w = rest.split()
    out, n = Path(w[0]).resolve(), int(w[1]) if len(w) > 1 else 3000
    with Halted(g):
        area, steps, first = None, {}, None
        for i in range(n):
            state = None
            try:        # before the game is loaded the probe can read unmapped memory
                if area is None:
                    bases(g)
                    area = _long(g, 4) - 0x1000 + PALETTE_AREA
                state = struct.unpack('>H', _bytes(g, area + PALETTE_STATE, 2))[0]
            except RuntimeError:
                pass
            if state is not None:
                if state == 2:
                    break
                if 0x11 <= state <= 0x17:
                    steps[state - 0x10] = steps.get(state - 0x10, 0) + 1
                    first = i if first is None else first
            g.cmd('monitor fields 1')
        else:
            raise RuntimeError(f'no finished palette build within {n} fields (CUSTOM5=1?)')
        _dump(g, area, PALETTE_END, out)
    seen = (f'building for {sum(steps.values())} fields from field {first}, by step: ' +
            ' '.join(f'{k}:{v}' for k, v in sorted(steps.items()))) if steps else \
        'already done when first seen'
    return f'palette done at field {i}, {seen}; area at ${area:08x} into {out}'


POS_X, POS_Z = 0x61d7c, 0x61d88    # player 1's x and z (longs, 16.16; forward is +sin, +cos)


def _pos(g):
    x, z = (struct.unpack('>i', _bytes(g, addr(g, o), 4))[0] / 65536 for o in (POS_X, POS_Z))
    return x, z, _angle(g, addr(g, ANGLE))


def cmd_pos(server, g, rest):
    with Halted(g):
        x, z, a = _pos(g)
    return f'x {x:.0f} z {z:.0f} angle {a}'


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
    ('floors', [(0x1d27a, 0x1fce0), (0x20f4c, 0x21160)]),
    ('bump', [(0x1fce0, 0x20f4c)]),
    ('objects', [(0x21160, 0x3fefa)]),
    ('interrupts', [(0x3fefa, 0x3ff5a), (0x415d8, 0x41800), (0x9b2dc, 0xad9e8)]),
]
WAITVBL_CALL = 0x3e58   # the main loop's jsr to the slave's _waitvbl (PL_PS)
# Enhanced resolution's display (src/display.s), by the release build's labels: the slave
# offsets come from its listing (the run's BUILD), the runtime base from _waitvbl
SLAVE_LST = (Path(__file__).resolve().parents[1] / 'tmp/build' / os.environ.get('BUILD', 'release')
             / 'AlienBreed3D.lst')
SLAVE_CATEGORIES = [
    ('c2p', 'c2p1x1_8_c5_030_2', 'c2p1x1_8_c5_030_2_scroffs'),
    ('convert', '_ds_small', '_ds_hunk0'),       # the frame to pens, 1x1, 2x2 or 3x3
    ('wait', '_ds_wait', '_ds_build'),          # until the back screen is not shown
    ('present', '_p_show', '_ds_small'),        # the rest: heads, c2p calls, the switch
]


def _slave_labels():
    if not SLAVE_LST.exists():
        return {}
    out = {}
    for line in SLAVE_LST.read_text(errors='replace').splitlines():
        m = re.match(r'^([0-9A-F]{8}) (\w+)$', line)
        if m:
            out[m.group(2)] = int(m.group(1), 16)
    return out


def _layout(g):
    """Hunk bases and the slave's _waitvbl (26 bytes; another loop's frame wait), from the
    jsr the slave patched in."""
    call = _bytes(g, addr(g, WAITVBL_CALL), 6)
    if call[:2] != b'\x4e\xb9':
        raise RuntimeError(f'no jsr at ${WAITVBL_CALL:x}: {call.hex()}')
    lay = {'hunks': bases(g), 'waitvbl': struct.unpack('>I', call[2:])[0]}
    labels = _slave_labels()
    if '_p_show' in labels:
        base = lay['waitvbl'] - labels['_waitvbl']
        # the conversion starts at _ds_small with LORES, else at _ds_one
        conv = '_ds_small' if '_ds_small' in labels else '_ds_one'
        lay['slave_base'] = base
        lay['slave'] = [(name, base + labels[a.replace('_ds_small', conv)],
                         base + labels[b.replace('_ds_small', conv)])
                        for name, a, b in SLAVE_CATEGORIES]
    return lay


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
        for name, lo, hi in layout.get('slave', ()):
            if lo <= pc < hi:
                return name, None
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
    out = Path(w[1]).resolve()
    prof = out.with_suffix('.prof')
    fields, pcs, spcs = [], {}, {}
    with Halted(g):
        n, inputs, until = _turn(g, ' '.join([w[0]] + w[2:]))
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
                elif 'slave_base' in lay and c not in ('wait', 'rom'):
                    t = spcs.setdefault(pc - lay['slave_base'], [0, 0, 0, c])
                    t[0] += units
                    t[1] += execs
                    t[2] += chip
            d = _long(g, a)
            fields.append({'units': h['units'], 'gap': h['gap'], 'high': h.get('high', 0),
                           'tail': h['tail'], 'chip': h['chip_units'], 'cats': cats, 'execs': execs_by,
                           'swap': d != st['last'], 'vsyncs': h['vsyncs']})
            st['last'] = d
            st['header'] = h
        n = run_fields(g, n, inputs, after, until)
        g.cmd(f'monitor aprof stop {prof}', timeout=120)
        prof.unlink(missing_ok=True)
    if until and n == TURN_MAX:
        raise RuntimeError(f'no full turn in {n} fields (keyboard control, K?)')
    h = st['header']
    meta = {k: h[k] for k in ('cycleunit', 'CYCLE_UNIT', 'colorclock_hz', 'cpu_model', 'cacr')}
    # the slave listing's build and the CPU clock, for frametime.py's clocks a pixel
    meta['build'] = os.environ.get('BUILD', 'release')
    hz = re.search(r'uae_cpu_frequency=(\d+)', os.environ.get('EXTRA_ARGS', ''))
    if hz:
        meta['cpu_hz'] = int(hz.group(1))
    out.write_text(json.dumps({'meta': meta, 'layout': lay, 'fields': fields,
                               'pcs': {f'{k:x}': v for k, v in sorted(pcs.items())},
                               'slave_pcs': {f'{k:x}': v for k, v in sorted(spcs.items())}}))
    return f'{n} fields captured into {out} ({sum(f["swap"] for f in fields)} swaps)'


COPPER_REGS = {
    0x080: 'COP1LCH', 0x082: 'COP1LCL', 0x084: 'COP2LCH', 0x086: 'COP2LCL', 0x088: 'COPJMP1',
    0x08a: 'COPJMP2', 0x08e: 'DIWSTRT', 0x090: 'DIWSTOP', 0x092: 'DDFSTRT', 0x094: 'DDFSTOP',
    0x096: 'DMACON', 0x09c: 'INTREQ', 0x100: 'BPLCON0', 0x102: 'BPLCON1', 0x104: 'BPLCON2',
    0x106: 'BPLCON3', 0x108: 'BPL1MOD', 0x10a: 'BPL2MOD', 0x10c: 'BPLCON4', 0x1fc: 'FMODE',
    0x1fe: 'NOP'}
TEMPLATE, PANELCOP, VIEW_LINE = 0x9a07c, 0x9a262, 416


def copper_text(data, at):
    """Copper list `data` (from game offset or address `at`) as text, to its end or COPJMP2."""
    out, run, bank = [], [], (0, 0)

    def flush():
        if run:
            o, first, vals = run[0][0], run[0][1], [v for _, _, v in run]
            out.append(f'${o:x} COLOR{first:02d}-{first + len(vals) - 1:02d} bank {bank[0]}'
                       f'{" LOCT" if bank[1] else ""}: ' + ' '.join(f'{v:03x}' for v in vals))
            run.clear()
    for i in range(0, len(data) - 3, 4):
        a, b = struct.unpack('>HH', data[i:i + 4])
        o = at + i
        if not a & 1 and 0x180 <= a < 0x1c0 and (not run or a == 0x180 + 2 * (run[0][1] + len(run))):
            run.append((o, (a - 0x180) // 2, b))
            continue
        flush()
        if not a & 1 and 0x180 <= a < 0x1c0:
            run.append((o, (a - 0x180) // 2, b))
        elif a & 1:
            out.append(f'${o:x} {"SKIP" if b & 1 else "WAIT"} {a:04x},{b:04x}')
        else:
            name = COPPER_REGS.get(a) or (f'BPL{(a - 0xe0) // 4 + 1}PT{"HL"[(a // 2) & 1]}' if 0xe0 <= a < 0x100
                                          else f'SPR{(a - 0x120) // 4}PT{"HL"[(a // 2) & 1]}' if 0x120 <= a < 0x140
                                          else f'${a:03x}')
            if a == 0x106:
                bank = (b >> 13, (b >> 9) & 1)
            out.append(f'${o:x} {name} = {b:04x}')
        if a == 0xffff and b == 0xfffe and i or a == 0x8a:
            break
    flush()
    return '\n'.join(out)


def cmd_copper(server, g, rest):
    w = rest.split()
    what = w[0] if w else 'template'
    with Halted(g):
        if what == 'view':
            line = int(w[1], 0) if len(w) > 1 else 0
            a = _long(g, addr(g, DRAWPT)) + line * VIEW_LINE
            return copper_text(_bytes(g, a, VIEW_LINE), a)
        off = {'template': TEMPLATE, 'panel': PANELCOP}[what]
        return copper_text(_bytes(g, addr(g, off), 0xac0 if what == 'panel' else 0x1e0), off)


def cmd_batch(server, g, rest):
    with Halted(g):
        return ''.join(g.cmd(c, timeout=600).rstrip('\n') + '\n'
                       for c in rest.split(' ;; ') if c.strip())


server = game_server('ab3d', commands={
    'base': cmd_base, 'peek': cmd_peek, 'level': cmd_level, 'full': cmd_full,
    'frames': cmd_frames, 'play': cmd_play, 'aprof': cmd_aprof, 'copper': cmd_copper,
    'batch': cmd_batch, 'next': cmd_next, 'grab': cmd_grab, 'holes': cmd_holes, 'tables': cmd_tables,
    'palette': cmd_palette, 'frame': cmd_frame, 'key': cmd_key, 'pause': cmd_pause, 'die': cmd_die, 'chunky': cmd_chunky,
    'end': cmd_end, 'pos': cmd_pos})

if __name__ == '__main__':
    server.main(sys.argv[1:])
