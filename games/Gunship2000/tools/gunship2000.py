#!/usr/bin/env python3
"""Gunship 2000 harness session on a native FS-UAE with the harness commands.

Library: Session(out, env) boots common/run.sh as its own instance (tmp/run/<instance>/, named
after `out` under tmp/) in warp, deterministic, with nothing in port 0 (the mouse comes from
`monitor mouse`), and drives it with fields(), key(), tap(), mouse(), click(), shot(),
profile(), aprof_start()/aprof_stop(), read() and quit().

Server: `python3 tools/gunship2000.py serve` boots under the shared gdb-stub server
(common/tools/game_server.py); `python3 tools/gunship2000.py <command>` sends it one command.

Environment: MACHINE picks an entry of MACHINES (default a1200-030; a500 is game.conf's ECS
machine, VARIANT=Gunship2000ECS only; a1200-040-z3 a 68040 with Zorro III fast); VARIANT (default Gunship2000AGA), SLAVE, BUILD and the
other common/run.sh options pass through;
GUNSHIP2000_FSUAE picks another native build (default the aprof one, which also has
`monitor mouse`, `input`, `key` and `fields`).
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401,E402
from amigaxdev import barto  # noqa: E402
from amigaxdev.gdbserve import Server, require_harness  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parents[1] / 'common'
FSUAE = os.environ.get('GUNSHIP2000_FSUAE') or os.path.join(os.environ['AMIGA_SHARE'], 'fs-uae-aprof/fs-uae')

# Machines. aprof needs a cycle-exact core without an MMU model, so the profiling 68030 is the
# shared a1200-030 (68030/50, instruction and data cache emulation, 2 MB chip, 8 MB fast) with
# the MMU model off; a1200-030-mmu is the preset unchanged (no instruction trace, no aprof).
MACHINES = {
    'a1200-fast': dict(SETUP='a1200-fast'),
    'a1200-030': dict(SETUP='a1200-030', EXTRA_ARGS='--uae_mmu_model=0'),
    'a1200-030-mmu': dict(SETUP='a1200-030'),
    'a500': dict(SETUP='custom'),   # game.conf's ECS machine: 68000, 1 MB chip, 2 MB fast
    # a 68040 with 32 MB of Zorro III fast memory (above 16 MB) for
    # WHDLoad's MMU option (WHD_ARGS=MMU); functional checks only, no timing
    'a1200-040-z3': dict(SETUP='a1200-040', EXTRA_ARGS='--zorro3_memory=32768'),
}

# Amiga raw key codes.
KEYS = dict(ret=0x44, enter=0x43, esc=0x45, space=0x40, bs=0x41, tab=0x42, del_=0x46,
            up=0x4c, down=0x4d, right=0x4e, left=0x4f, lshift=0x60, ctrl=0x63, lalt=0x64,
            f1=0x50, f2=0x51, f3=0x52, f4=0x53, f5=0x54, f6=0x55, f7=0x56, f8=0x57, f9=0x58,
            f10=0x59)
for i, c in enumerate('1234567890'):
    KEYS[c] = 0x01 + i
for c, k in zip('qwertyuiop', range(0x10, 0x1a)):
    KEYS[c] = k
for c, k in zip('asdfghjkl', range(0x20, 0x29)):
    KEYS[c] = k
for c, k in zip('zxcvbnm', range(0x31, 0x38)):
    KEYS[c] = k
BUTTONS = {1: 'JOY1_FIRE_BUTTON', 2: 'JOY1_2ND_BUTTON'}  # port-0 mouse: left, right


def instance_for(out):
    """common/run.sh INSTANCE for a session directory: its path under tmp/ as a plain name."""
    try:
        rel = str(out.relative_to(ROOT / 'tmp'))
    except ValueError:
        rel = hashlib.sha256(str(out).encode()).hexdigest()[:12]
    return 'session-' + re.sub(r'[^A-Za-z0-9_-]', '-', rel)


def machine():
    return dict(MACHINES[os.environ.get('MACHINE') or 'a1200-030'])


class Session:
    def __init__(self, out, env=None):
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.instance = instance_for(self.out)
        self.run = ROOT / 'tmp/run' / self.instance / '.run'
        self.s = Server('gunship2000', str(ROOT), run_script=str(COMMON / 'run.sh'),
                        run_dir=str(self.run), profile_window=False)
        base = dict(GAME=ROOT.name, INSTANCE=self.instance,
                    VARIANT=os.environ.get('VARIANT') or 'Gunship2000AGA', FSUAE=FSUAE,
                    WARP='1', DETERMINISTIC='1', JOY0='none', WINDOW='none')
        if os.environ.get('SLAVE'):
            base['SLAVE'] = str(Path(os.environ['SLAVE']).resolve())
        base.update(machine())
        base.update(env or {})
        self.env = base
        self.g = self.s.boot(base)
        self.field = 0
        require_harness(self.g, 'key', 'fields', 'mouse', 'input')

    def cmd(self, text, timeout=600):
        r = self.g.cmd(text, timeout=timeout)
        checked = r.replace('FILESYS: EXALL called twice with ERROR_NO_MORE_ENTRIES', '')
        if any(x in checked for x in ('ERROR', 'not supported', 'Undefined', 'Protocol error')):
            raise RuntimeError(r)
        return r

    def fields(self, n):
        while n > 0:
            k = min(n, 6000)
            self.cmd(f'monitor fields {k}')
            self.field += k
            n -= k

    def key(self, name, down):
        k = KEYS[name] if isinstance(name, str) else name
        self.cmd(f'monitor key {k:x} {int(down)}')

    def tap(self, name, hold=3, after=3):
        self.key(name, 1)
        self.fields(hold)
        self.key(name, 0)
        self.fields(after)

    def type(self, text, hold=3, after=3):
        for c in text:
            self.tap(c, hold, after)

    def mouse(self, dx, dy, settle=2):
        # Steps of at most 64 counts with fields between them: the counters are 8 bits.
        while dx or dy:
            sx, sy = max(-64, min(64, dx)), max(-64, min(64, dy))
            self.cmd(f'monitor mouse {sx} {sy}')
            self.fields(settle)
            dx, dy = dx - sx, dy - sy

    def click(self, button=1, hold=4, after=4):
        self.cmd(f'monitor input {BUTTONS[button]} 1')
        self.fields(hold)
        self.cmd(f'monitor input {BUTTONS[button]} 0')
        self.fields(after)

    def shot(self, name):
        """A screenshot of the next field (a one-field trace) to OUT/name."""
        p = self.run / 'shot.bin'
        p.unlink(missing_ok=True)
        self.cmd(f'monitor profile 1 "" "{p}"')
        self.field += 1
        f = barto.load(str(p)).fields[-1]
        if not f.shot:
            raise RuntimeError('the traced field has no screenshot')
        (self.out / name).write_bytes(f.shot)
        return self.out / name

    def profile(self, n, path):
        r = self.cmd(f'monitor profile {n} "" "{Path(path).resolve()}"', timeout=3600)
        self.field += n
        return r

    def aprof_start(self):
        return self.cmd('monitor aprof start')

    def aprof_stop(self, path):
        return self.cmd(f'monitor aprof stop {Path(path).resolve()}', timeout=1800)

    def read(self, addr, n):
        # gdb's dump takes no quoted file name: a temporary file in the game's tmp/.
        fd, p = tempfile.mkstemp(prefix='mem-', dir=str(ROOT / 'tmp'))
        os.close(fd)
        try:
            self.cmd(f'dump binary memory {os.path.relpath(p)} {addr:#x} {addr + n:#x}')
            return Path(p).read_bytes()
        finally:
            os.unlink(p)

    def long(self, addr):
        return int.from_bytes(self.read(addr, 4), 'big')

    def word(self, addr):
        return int.from_bytes(self.read(addr, 2), 'big')

    def regs(self, names='pc'):
        return self.cmd('info registers ' + names)

    def quit(self):
        try:
            self.g.cmd('kill', timeout=10)
        except Exception:
            pass
        # common/run.sh stop kills only the emulator this instance recorded.
        subprocess.run(['bash', str(COMMON / 'run.sh'), 'stop'],
                       env=dict(os.environ, GAME=ROOT.name, INSTANCE=self.instance),
                       capture_output=True)


if __name__ == '__main__':
    sys.path.insert(0, str(COMMON / 'tools'))
    from game_server import game_server
    game_server('gunship2000', profile_window=False).main(sys.argv[1:])
