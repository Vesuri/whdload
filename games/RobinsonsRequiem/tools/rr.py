#!/usr/bin/env python3
"""The gdb-stub game server (common/tools/game_server.py).

    python3 tools/rr.py serve        boot (common/run.sh with DEBUG=1), attach gdb, listen
    python3 tools/rr.py wait 30      let it run
    python3 tools/rr.py shot x.png   screenshot of the next field
    python3 tools/rr.py quit         stop gdb and the emulator

The run options of common/run.sh apply to serve through the environment (VARIANT=
RobinsonsRequiemAGA, SLAVE=original, SETUP=a1200-030, WARP=1 WINDOW=none, ...).

Game commands (AGA game only):

    opens            log every file the game opens (Open, Lock) to .run/opens.log
    ingame [low]     from boot to the jungle start: English, the intro skipped with Esc, level
                     of detail and 3D window set to HIGH (`low` keeps both LOW), Start
    point X Y        move the pointer to (X, Y) of a `shot` (754x576), from the top-left corner
    click            press and release the left mouse button
    key RAW          press and release raw key RAW (hex), e.g. 45 for Esc
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
from game_server import game_server  # noqa: E402

# START (AGA), code hunk 0: the open wrapper's first instructions (+$2546) and the calls in it.
# The game's name buffer is passed in d1 to dos.library Open (+$255e, MODE_READWRITE; +$267e,
# MODE_NEWFILE) and Lock (+$2590).
HUNK0_SIG = '0x48e7, 0x60c0, 0x2208, 0x61c8, 0x243c'
HUNK0_SIG_OFFSET = 0x2546
CALLS = {'open': 0x255e, 'new': 0x267e, 'lock': 0x2590}

# Pointer targets in `shot` coordinates (754x576). A mouse count moves the pointer one shot
# pixel; the pointer is homed to the top-left corner (ORIGIN) before each move.
ORIGIN = (75, 70)
FLAG_UK = (397, 258)
LOD = (160, 130)
WINDOW = (165, 380)
START = (395, 390)

RAW_ESC = 0x45


def run_fields(g, n):
    g.stop()
    g.cmd(f'monitor fields {n}', timeout=120)


def mouse(g, dx, dy):
    """Steps of at most 10 counts per two fields: larger ones wrap the game's counters."""
    while dx or dy:
        sx, sy = max(-10, min(10, dx)), max(-10, min(10, dy))
        g.cmd(f'monitor mouse {sx} {sy}')
        run_fields(g, 2)
        dx, dy = dx - sx, dy - sy


def point(g, x, y):
    mouse(g, -800, -600)
    mouse(g, x - ORIGIN[0], y - ORIGIN[1])


def click(g):
    g.stop()
    g.cmd('monitor input JOY1_FIRE_BUTTON 1')
    run_fields(g, 4)
    g.cmd('monitor input JOY1_FIRE_BUTTON 0')
    run_fields(g, 10)


def key(g, raw):
    g.stop()
    g.cmd(f'monitor key {raw:x} 1')
    run_fields(g, 3)
    g.cmd(f'monitor key {raw:x} 0')
    run_fields(g, 3)


class Opens:
    """Breakpoints on the open wrapper that append 32 bytes of the name to one file per call."""

    def __init__(self, server):
        self.dir = Path(server.run_dir)
        self.armed = False

    def arm(self, g):
        if self.armed:
            return
        g.stop()
        out = g.cmd(f'find /h 0x200000, 0x1000000, {HUNK0_SIG}', timeout=120)
        hits = [int(w, 16) for w in out.split('\n') if re.fullmatch(r'0x[0-9a-f]+', w.strip())]
        # The PRELOAD copy of the file comes first; the loaded segment is the last match.
        if not hits:
            raise RuntimeError('START hunk 0 not found (not loaded yet?): ' + out)
        base = hits[-1] - HUNK0_SIG_OFFSET
        script = self.dir / 'opens.gdb'
        lines = []
        for name, off in CALLS.items():
            (self.dir / f'{name}.bin').unlink(missing_ok=True)
            lines += [f'break *{base + off:#x}', 'commands', 'silent',
                      f'append memory {self.dir}/{name}.bin $d1 $d1+32', 'continue', 'end']
        script.write_text('\n'.join(lines) + '\n')
        g.cmd(f'source {script}')
        self.armed = True
        return base

    def names(self, which='open'):
        p = self.dir / f'{which}.bin'
        if not p.exists():
            return []
        b = p.read_bytes()
        return [b[i:i + 32].split(b'\0')[0].decode('latin1') for i in range(0, len(b), 32)]

    def wait(self, g, name, timeout=60):
        """Run until the game opens NAME (case-insensitive); stopped on return."""
        end = time.time() + timeout
        while time.time() < end:
            if any(n.lower() == name.lower() for n in self.names()):
                g.stop()
                return
            g.cont()
            time.sleep(0.25)
        g.stop()
        raise TimeoutError(f'{name} not opened in {timeout} s; opened: {self.names()}')


def esc_until(g, o, name, tries=60):
    """Press Esc, run a second, until the game opens NAME."""
    for _ in range(tries):
        key(g, RAW_ESC)
        try:
            return o.wait(g, name, timeout=1)
        except TimeoutError:
            pass
    o.wait(g, name, timeout=1)


def opens_cmd(server, g, rest):
    o = server.opens
    base = o.arm(g)
    g.cont()
    return (f'hunk 0 at {base:#x}; ' if base else '') + 'opened: ' + ' '.join(o.names())


def ingame(server, g, rest):
    o = server.opens
    g.stop()
    t0 = time.time()
    # Hunk 0 is in memory once the language screen's data loads; wait for the segment.
    for _ in range(40):
        try:
            o.arm(g)
            break
        except RuntimeError:
            g.cont()
            time.sleep(0.5)
    esc_until(g, o, 'flags.DO')     # Esc ends the Silmarils logo
    run_fields(g, 50)
    point(g, *FLAG_UK)
    click(g)
    # An Esc during the logo skips the whole intro (flags.DO goes on to baratinu.DO). Later,
    # Esc ends the part that is running: the video (introag ... introj) as one, then the
    # title (present, musique2) and the credits (authors) each on their own. Press it until
    # the options menu (prefsu) reads CONFIG.INF.
    esc_until(g, o, 'CONFIG.INF')
    run_fields(g, 50)
    if rest.strip() != 'low':
        point(g, *LOD)
        click(g)
        point(g, *WINDOW)
        click(g)
    point(g, *START)
    click(g)
    o.wait(g, 'avion.DO', timeout=120)
    run_fields(g, 100)
    g.cont()
    return f'in game after {time.time() - t0:.0f} s; opened: ' + ' '.join(o.names())


def point_cmd(server, g, rest):
    x, y = map(int, rest.split())
    point(g, x, y)
    g.cont()
    return 'ok'


def click_cmd(server, g, rest):
    click(g)
    g.cont()
    return 'ok'


def key_cmd(server, g, rest):
    key(g, int(rest, 16))
    g.cont()
    return 'ok'


server = game_server('rr', commands={'opens': opens_cmd, 'ingame': ingame, 'point': point_cmd,
                                      'click': click_cmd, 'key': key_cmd})
server.opens = Opens(server)

if __name__ == '__main__':
    server.main(sys.argv[1:])
