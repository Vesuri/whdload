#!/usr/bin/env python3
"""Bounded live check of the player bolts' near plane (src/near_plane.s), CD32 English.

The direct-flight fixture (tools/flight_fixture.py --release) starts the first
Gimle mission with invincibility (CUSTOM2=2 CUSTOM3=4 CUSTOM4=0). The ship's
near plane, its radius, is 180 (46080 units); the Hornet's is 100. Space
fires the neutron gun, then G selects the mass driver and Space fires it. At
each picture's draw-list build (E:2c9b6) the first two player bolts of each
burst are read: native depth word (A4+9438, nonzero once projected) and the
staged position relative to the player. The forward distance at the first
projected picture must lie between the Hornet's plane and the ship's with the
enhanced framerate, and at or past the ship's plane in original mode (the
control: no hook). A screenshot of that picture is kept.
"""
import argparse
import json
import math
import re
import time
from pathlib import Path
import _amigaxdev  # noqa: F401
import wc_run
from amigaxdev import barto
from ocs_reconstruct import new_output, require
from variants import get
from cd32_runtime import locate

SITE = 0x19064          # flight controller ramp store: in flight
DRAW_LIST = 0x2c9b6     # the draw list build, after every slot's projection
NEAR, CLASS, OWNER, MODEL, DEPTH, POS, VEL = 7030, 5888, 14954, 6136, 9438, 4508, 7534
GUNS = (('neutron', 25), ('mass driver', 26))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path, help='a tools/flight_fixture.py --release build')
    p.add_argument('--output', required=True)
    p.add_argument('--original-mode', action='store_true', help='the control: CUSTOM5=8 (CPU-dependent, the original game), no hook')
    a = p.parse_args()
    out = new_output(a.output); out.mkdir(parents=True)
    v = get('cd32')
    whd = 'CUSTOM2=2 CUSTOM3=4 CUSTOM4=0 '+('CUSTOM5=8' if a.original_mode else 'CUSTOM5=1')+' DCACHE'
    env = wc_run.run_env(out, variant='cd32', SLAVE=str((a.build/'WingCommanderCD32.Slave').resolve()),
                         WARP='1', NTSC='0', WINDOW='front', JOY0='none', JOY1='none',
                         DETERMINISTIC='1', AMIGA_SETUP='a1200-030', WHD_ARGS=whd, EXTRA_ARGS='',
                         OCS_STOCK_CLOCK='0', INTRO_STOCK_CLOCK='0', WC_BASELINE_CACHE_MODEL='1')
    g = None

    def cmd(s, timeout=60):
        r = g.cmd(s, timeout=timeout)
        if any(x in r for x in ('Remote connection closed', 'Cannot access', 'Error', 'Protocol error')):
            raise RuntimeError(r)
        return r

    def until(addr, timeout=900):
        r = cmd(f'break *{addr:#x}\ncontinue\ndelete', timeout)
        if 'Breakpoint' not in r:
            raise ValueError('checkpoint missed: '+r)

    def num(expr):
        return int(re.search(r'VALUE (-?\d+)', cmd('printf "VALUE %d\\n", '+expr))[1])

    def shot(name):
        path = out/(name+'.bin')
        cmd(f'monitor profile 1 "" "{path}"', 60)
        (out/(name+'.png')).write_bytes(barto.load(str(path)).fields[-1].shot)
        path.unlink()

    def stop():
        nonlocal g
        if g:
            g.p.kill(); g = None
        wc_run.stop(env)

    rows = []
    try:
        g = wc_run.server('wc-near', env, profile_window=False).boot(env)
        snap = out/'calibration.bin'
        for _ in range(12):
            g.cont(); time.sleep(1); g.stop()
            cmd(f'dump binary memory {snap.resolve()} 0x200000 0xa00000')
            try:
                layout = locate(snap.read_bytes()); break
            except ValueError:
                pass
        else:
            raise ValueError('live segment chain not found')
        snap.unlink(); stop()
        g = wc_run.server('wc-near', env, profile_window=False).boot(env)
        h0, h1 = layout['hunks'][:2]
        a4 = h1+v.A4_BASE
        w = lambda off: num(f'*(short*){a4+off:#x}')
        L = lambda off: num(f'*(int*){a4+off:#x}')
        until(h0+SITE)
        cmd('monitor fields 50')
        for name, model in GUNS:
            if model != GUNS[0][1]:
                cmd('monitor key 24 1'); cmd('monitor fields 3'); cmd('monitor key 24 0'); cmd('monitor fields 20')
            cmd('monitor key 40 1')
            first = None
            for picture in range(40):
                until(h0+DRAW_LIST)
                bolts = [k for k in range(10, 32) if w(CLASS+2*k) == 8 and w(MODEL+2*k) == model
                         and num(f'*(signed char*){a4+OWNER+k:#x}') == 0]
                for k in bolts[:2]:
                    if w(DEPTH+2*k):
                        pos = [L(POS+12*k+4*i)-L(POS+4*i) for i in range(3)]
                        vel = [L(VEL+12*k+4*i) for i in range(3)]
                        forward = sum(x*y for x, y in zip(pos, vel))/math.sqrt(sum(y*y for y in vel))
                        first = dict(gun=name, picture=picture, slot=k, near=w(NEAR), forward=round(forward), pos=pos)
                        break
                if first:
                    break
            require(first, f'{name}: no projected player bolt')
            shot(name.replace(' ', '-'))
            cmd('monitor key 40 0'); cmd('monitor fields 40')
            rows.append(first); print(first, flush=True)
    finally:
        stop()
    for r in rows:
        require(r['near'] == 180, ('ship plane', r))
        if a.original_mode:
            require(r['forward'] >= 180*256, ('native plane', r))
        else:
            require(100*256 <= r['forward'] < 180*256, ('player bolt plane', r))
    (out/'report.json').write_text(json.dumps(dict(passed=True, original_mode=a.original_mode, bolts=rows), indent=2)+'\n')
    print('near plane live:', 'original' if a.original_mode else 'enhanced', [(r['gun'], r['forward']) for r in rows])


if __name__ == '__main__':
    main()
