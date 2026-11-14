#!/usr/bin/env python3
"""Profile the jungle start with keypad 9 held: rr_prof.py OUT (docs/performance.md)

The workload: a developer-type build's direct start (docs/development.md; for the AGA game
by default BUILD=profile, the developer build plus a frame counter; another from game.conf
with BUILD=), SETTLE fields (default 150) after the game opens avion.DO (.CO), then keypad
9 (forward and to the right) held for FIELDS fields (default 500, 10 s PAL); KEY=hex another
raw key, KEY=none none. The ECS game: VARIANT=RobinsonsRequiem SETUP=custom BUILD=developer
BARTO=1 (its 68000 cannot run under aprof; frames from FRAME_MARK).

Boots deterministically (WARP=1 DETERMINISTIC=1 JOY0=none, INSTANCE=prof); the run options
of common/run.sh apply through the environment (SETUP, FSUAE, EXTRA_ARGS, BUILD, ...). From
the reset it runs chunks of 10 fields until START's hunk 0 is loaded, then stops at the
dos.library Open of avion.DO or .CO (a conditional breakpoint on hunk 0's Open, rr.py's
LAYOUTS: +$255e AGA, +$1b0e ECS), deletes it and
runs SETTLE fields. The window then runs with keypad 9 down:

    APROF=1   under `monitor aprof start/stop` (FSUAE=$FSUAE_APROF, a CPU without MMU:
              EXTRA_ARGS=--uae_mmu_model=0 on a1200-030), into OUT/window.prof
    BARTO=1   as chained 100-field `monitor profile` traces (any cycle-exact 68000-68030
              core, the ECS game's 68000 too), each reduced with amigaxdev.callprofile and
              deleted: OUT/window.pkl.gz, with the presented frames timestamped (FRAME_MARK)
              and call stacks through START's hunks in fast memory (code_in_fast)
    else      plain `monitor fields`

Before and after the window it saves screenshots (start.png, end.png) and reads the frame
counter into OUT/run.json, with the hunk bases, the slave's address (PROFILE_SLAVE) and
hash and the machine options.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
from amigaxdev import barto, callprofile  # noqa: E402
from amigaxdev.callprofile import Reduction  # noqa: E402
from amigaxdev.gdbserve import Server, require_harness  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT.parents[1] / 'common'
sys.path.insert(0, str(COMMON / 'tools'))
from rr import find_hunk0, layout  # noqa: E402

# The profile build's frame counter (src/, PROFILE_FRAMES): frames drawn since boot.
PROFILE_FRAMES = 0x10c
PROFILE_SLAVE = 0x110       # and the slave's address
# Hunk 0: the beam wait before each buffer swap, entered once per presented frame.
FRAME_MARK = {'RobinsonsRequiemAGA': 0x13ce, 'RobinsonsRequiem': 0xcac}
# START's variables read with the counters: (hunk, offset, bytes). The frame wait (AGA hunk 1
# +$49e8, ECS +$30ac) holds each frame until `fields` reaches `cap`; the VBL counts both.
GAME_VARS = {'RobinsonsRequiemAGA': {'cap': (1, 0xee6a, 1), 'fields': (1, 0xee6b, 1),
                                     'vbl': (1, 0xee6c, 4)},
             'RobinsonsRequiem': {'cap': (1, 0xd4c0, 1), 'fields': (1, 0xd4c1, 1)}}


class Session:
    def __init__(self, out):
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.instance = os.environ.get('INSTANCE', 'prof')
        self.run = ROOT / 'tmp/run' / self.instance / '.run'
        self.s = Server('rrprof', str(ROOT), run_script=str(COMMON / 'run.sh'),
                        run_dir=str(self.run), profile_window=False)
        env = dict(GAME=ROOT.name, INSTANCE=self.instance, BUILD='profile',
                   VARIANT='RobinsonsRequiemAGA', SETUP='a1200-030', WARP='1',
                   DETERMINISTIC='1', JOY0='none', WINDOW='none', FSUAE_CLAIM_STRICT='1')
        env.update({k: os.environ[k] for k in env if k in os.environ})
        self.env = env
        self.g = self.s.boot(env)
        self.field = 0
        require_harness(self.g, 'key', 'fields')

    def cmd(self, text, timeout=900):
        r = self.g.cmd(text, timeout=timeout)
        if any(x in r for x in ('rror', 'not supported', 'Undefined')):
            raise RuntimeError(f'{text}: {r}')
        return r

    def fields(self, n):
        self.cmd(f'monitor fields {n}')
        self.field += n

    def read(self, addr, n):
        fd, p = tempfile.mkstemp(prefix='rr-mem-', dir=str(ROOT / 'tmp'))
        os.close(fd)
        try:
            self.cmd(f'dump binary memory {p} {addr:#x} {addr + n:#x}')
            return Path(p).read_bytes()
        finally:
            os.unlink(p)

    def shot(self, name):
        p = self.run / 'shot.bin'
        self.cmd(f'monitor profile 1 "" "{p}"')
        self.field += 1
        f = barto.load(str(p)).fields[-1]
        (self.out / name).write_bytes(f.shot)

    def quit(self):
        try:
            self.g.cmd('kill', timeout=10)
        except Exception:
            pass
        subprocess.run(['bash', str(COMMON / 'run.sh'), 'stop'],
                       env=dict(os.environ, GAME=ROOT.name, INSTANCE=self.instance),
                       capture_output=True)


def hunks(s, h0):
    """START's segment bases from hunk 0's (BPTR chain at base - 4)."""
    bases = [h0]
    while len(bases) < 8:
        nxt = int.from_bytes(s.read(bases[-1] - 4, 4), 'big')
        if not nxt:
            break
        bases.append(nxt * 4 + 4)
    return bases


def code_in_fast(segs):
    """Let callprofile find JSR/BSR in START's hunks wherever they are loaded.

    The reducer decodes opcodes from the trace's chip, slow and ROM snapshots only; START
    sits in fast memory on both default machines, so without this its calls build no stacks.
    segs: (base, bytes) of each hunk, read before the window (the code does not move).
    """
    chip_only = callprofile._opkind

    def opkind(t, pc, cache):
        k = cache.get(pc)
        if k is not None:
            return k
        for b, m in segs:
            if b <= pc < b + len(m) - 1:
                w = int.from_bytes(m[pc - b:pc - b + 2], 'big')
                k = cache[pc] = 1 if (w & 0xffc0) == 0x4e80 or (w & 0xff00) == 0x6100 else 0
                return k
        return chip_only(t, pc, cache)
    callprofile._opkind = opkind


def main():
    out = Path(sys.argv[1])
    fields = int(os.environ.get('FIELDS', 500))
    settle = int(os.environ.get('SETTLE', 150))
    aprof = os.environ.get('APROF') == '1'
    trace = os.environ.get('BARTO') == '1'
    # KEY=none: the control workload, standing still (the same view in every build)
    key = None if os.environ.get('KEY') == 'none' else int(os.environ.get('KEY', '3f'), 16)
    t0 = time.time()
    s = Session(out)
    try:
        base = None
        while base is None:
            if s.field > 3000:
                raise TimeoutError('START hunk 0 not found in 3000 fields')
            s.fields(10)
            try:
                base = find_hunk0(s.g, s.env['VARIANT'])
            except RuntimeError:
                pass
        # Stop at the Open of avion.DO ('avio' at d1): a deterministic point after boot.
        open_at = base + layout(s.env['VARIANT'])['calls']['open']
        s.cmd(f'break *{open_at:#x}')
        s.cmd('condition $bpnum *(unsigned int *)$d1 == 0x6176696f')
        r = s.g.cmd('continue', timeout=1200)
        pc = s.g.cmd('info registers pc')
        if f'{open_at:#x}' not in pc:
            raise RuntimeError(f'not stopped at the avion.DO open: {r} {pc}')
        name = s.read(int(s.g.cmd('info registers d1').split()[1], 16), 12)
        s.cmd('delete')
        found_at = s.field
        s.fields(settle)
        bases = hunks(s, base)

        def counters():
            # frames: the AGA profile builds only; elsewhere a constant, so 0 frames
            c = {'frames': int.from_bytes(s.read(PROFILE_FRAMES, 4), 'big')}
            for k, (h, o, n) in GAME_VARS[s.env['VARIANT']].items():
                c[k] = int.from_bytes(s.read(bases[h] + o, n), 'big')
            return c
        s.shot('start.png')
        c0 = counters()
        if key is not None:
            s.cmd(f'monitor key {key:x} 1')
        w0 = s.field
        if aprof:
            print(s.cmd('monitor aprof start'), flush=True)
            s.fields(fields)
            print(s.cmd(f'monitor aprof stop {(s.out / "window.prof").resolve()}', timeout=900),
                  flush=True)
        elif trace:
            # each hunk's allocation size (header included) is the longword before its BPTR
            code_in_fast([(b, s.read(b, int.from_bytes(s.read(b - 8, 4), 'big') - 8))
                          for b in bases])
            red = Reduction(marks={'frame': base + FRAME_MARK[s.env['VARIANT']]})
            chunk = s.run / 'chunk.bin'
            for start in range(0, fields, 100):
                n = min(100, fields - start)
                s.cmd(f'monitor profile {n} "" "{chunk}"', timeout=3600)
                s.field += n
                red.feed(str(chunk))
                chunk.unlink()
            red.save(s.out / 'window.pkl.gz')
        else:
            s.fields(fields)
        w1 = s.field
        c1 = counters()
        if key is not None:
            s.cmd(f'monitor key {key:x} 0')
        s.shot('end.png')
        slave = ROOT / 'tmp/build' / s.env['BUILD'] / f'{s.env["VARIANT"]}.Slave'
        frames = c1['frames'] - c0['frames']
        if trace:   # the frames the trace saw start (FRAME_MARK)
            frames = sum(1 for e in red.events if e[0] == 'frame')
        info = dict(env=s.env, key=None if key is None else f'{key:02x}', frames=frames, fps=round(50 * frames / (w1 - w0), 3), extra_args=os.environ.get('EXTRA_ARGS', ''),
                    fsuae=os.environ.get('FSUAE', ''), aprof=aprof, barto=trace,
                    slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),
                    avion_name=name.split(b'\0')[0].decode('latin1'), avion_field=found_at,
                    window=[w0, w1], hunks=[hex(b) for b in bases], counters=[c0, c1],
                    slave=hex(int.from_bytes(s.read(PROFILE_SLAVE, 4), 'big')),
                    host_seconds=round(time.time() - t0))
        (s.out / 'run.json').write_text(json.dumps(info, indent=1) + '\n')
        print(json.dumps(info, indent=1))
    finally:
        s.quit()


if __name__ == '__main__':
    main()
