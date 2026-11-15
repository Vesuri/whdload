#!/usr/bin/env python3
"""Bounded live world-speed check on a release build (English).

Boots the release slave with one CUSTOM5 value (bit 0 enhanced framerate,
bits 1-3 world speed: 1-4 = 1.0x/1.2x/1.5x/2.0x), skips the intro with the
left button, clicks into the simulator flight (as mouse_live_check.py --flight
does) and counts world ticks and drawn flight pictures over a fixed number of
emulated display fields. The rate is emulated time, not wall time: it shows
what the slave schedules on the chosen machine, not real-hardware speed.

--intro measures the title world instead (no clicks). --bolts N holds fire
(space) in the flight and samples the player's cannon bolts at the end of each
of N staged pictures: between pictures every bolt must advance by exactly its
velocity times rate/Hz per display field. Pictures where the predictor's lead
bound (one tick plus two fields) applied are excluded and counted; that bound
limits every object, not only bolts.
"""
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
import _amigaxdev  # noqa: F401
import wc_run
from ocs_reconstruct import new_output
from variants import get
from mouse_live_check import GAMES

RATES = {1: 10, 2: 12, 3: 15, 4: 20}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant', choices=('ocs', 'cd32'))
    p.add_argument('build', type=Path)
    p.add_argument('--custom5', type=int, required=True, choices=range(2, 10))
    p.add_argument('--fields', type=int, default=100,
                   help='measured span in display fields; the simulator flight ends after about 55 world ticks')
    p.add_argument('--setup', default='a1200-030', help='AMIGA_SETUP')
    p.add_argument('--output', required=True)
    p.add_argument('--intro', action='store_true', help='measure the title world, not the flight')
    p.add_argument('--bolts', type=int, metavar='N', help='check player bolt motion over N pictures')
    a = p.parse_args()
    out = new_output(a.output); out.mkdir(parents=True)
    ocs = a.variant == 'ocs'; game = GAMES[a.variant]; v = get(a.variant)
    speed, framerate = a.custom5 >> 1, a.custom5 & 1
    if ocs:
        from ocs_runtime import locate
        slave = a.build/'WingCommander.Slave'
        sy = json.loads((a.build/'build.json').read_text())['symbols']
        names = dict(ticks='ocs_intro_completed' if a.intro else 'ocs_clock_completed', pictures='ocs_clock_drawn', active='ocs_clock_active', hz='ocs_clock_hz')
    else:
        from cd32_runtime import locate
        slave = a.build/'WingCommanderCD32.Slave'
        sy = {n: int(o, 16) for o, n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
        names = dict(ticks='timing_completed', pictures='timing_pictures', active='timing_active', hz='timing_hz')
    length = 0x400000 if ocs else 0x800000
    env = wc_run.run_env(out, variant=a.variant, SLAVE=str(slave.resolve()),
                         WARP='1', NTSC='0', WINDOW='front', JOY0='none', JOY1='none',
                         DETERMINISTIC='1', AMIGA_SETUP=a.setup, WHD_ARGS=f'CUSTOM5={a.custom5} DCACHE',
                         EXTRA_ARGS='--fast_memory=4096' if ocs and a.setup != 'a500' else '', OCS_STOCK_CLOCK='0',
                         INTRO_STOCK_CLOCK='0', WC_BASELINE_CACHE_MODEL='0' if a.setup == 'a500' else '1')
    g = None

    def stop():
        nonlocal g
        if g:
            g.p.kill(); g = None
        wc_run.stop(env)

    def cmd(s, timeout=60):
        r = g.cmd(s, timeout=timeout)
        if any(x in r for x in ('Remote connection closed', 'Cannot access', 'Error', 'Invalid hex', 'Protocol error')):
            raise RuntimeError(r)
        return r

    def until(addr, timeout=60):
        r = cmd(f'break *{addr:#x}\ncontinue\ndelete', timeout)
        if 'Breakpoint' not in r:
            raise ValueError('checkpoint missed: '+r)

    def number(expr):
        return int(re.search(r'VALUE (-?\d+)', cmd('printf "VALUE %d\\n", '+expr))[1])

    try:
        g = wc_run.server('wc-speed', env, profile_window=False).boot(env)
        snapshot = out/'calibration.bin'
        for _ in range(12):
            g.cont(); time.sleep(1); g.stop()
            cmd(f'dump binary memory {snapshot.resolve()} 0x200000 {0x200000+length:#x}')
            try:
                layout = locate(snapshot.read_bytes()); break
            except ValueError:
                pass
        else:
            raise ValueError('live segment chain not found')
        snapshot.unlink(); stop()
        g = wc_run.server('wc-speed', env, profile_window=False).boot(env)
        h0, h1, _, _ = layout['hunks']; a4 = h1+v.A4_BASE; sb = layout['slave']
        var = lambda name, kind='int': number(f'*({kind}*){sb+sy[name]:#x}')
        field = a4+game['field']
        if a.intro:
            until(sb+sy['intro_title'], 600)
            cmd('monitor fields 10')
            def intro_sample():
                return dict(field=number(f'*(unsigned int*){field:#x}'), ticks=var(names['ticks']),
                            rate=var('timing_world_rate'), active=var('intro_active', 'short'), hz=var(names['hz']))
            first = intro_sample(); cmd(f'monitor fields {a.fields}', 120); last = intro_sample()
            fields = last['field']-first['field']
            result = dict(variant=a.variant, setup=a.setup, custom5=a.custom5, scene='intro',
                          slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(), first=first, last=last,
                          fields=fields, world_hz=(last['ticks']-first['ticks'])*first['hz']/fields,
                          expected_world_hz=RATES[speed])
            (out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(result))
            assert first['active'] == 1 and last['active'] == 1, 'measurement left the intro'
            assert first['rate'] == RATES[speed], 'intro world rate not selected'
            return
        for wait, done in game['intro']:
            until(h0+wait)
            cmd('monitor input JOY1_FIRE_BUTTON 1')
            until(h0+done)
            cmd('monitor input JOY1_FIRE_BUTTON 0')
        menu, _ = game['menu']
        until(h0+menu); cmd('monitor fields 4'); until(h0+menu)
        if ocs:     # OCS starts over the absent Secret Missions option; move to Vega.
            for _ in range(10):
                cmd('monitor mouse 0 -4'); cmd('monitor fields 1')
            cmd('monitor fields 10'); until(h0+menu)
        cmd('monitor input JOY1_FIRE_BUTTON 1'); cmd('monitor fields 3')
        cmd('monitor input JOY1_FIRE_BUTTON 0')
        until(h0+game['flight'][0], 600)
        cmd('monitor fields 5')                        # settle past flight entry
        if a.bolts:
            bolts(a, cmd, until, var, names, sb, sy, a4, v, ocs, slave, out)
            return
        def sample():
            return dict(field=number(f'*(unsigned int*){field:#x}'), ticks=var(names['ticks']),
                        pictures=var(names['pictures']), active=var(names['active'], 'short'),
                        rate=var('timing_world_rate'), hz=var(names['hz']),
                        framerate=var('timing_high_framerate', 'short'), flight_rate=var('timing_flight_rate'))
        first = sample(); cmd(f'monitor fields {a.fields}', 120); last = sample()
        fields = last['field']-first['field']; seconds = fields/first['hz']
        result = dict(variant=a.variant, setup=a.setup, custom5=a.custom5, speed=speed, framerate=framerate,
                      slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(), first=first, last=last,
                      fields=fields, seconds=seconds,
                      world_hz=(last['ticks']-first['ticks'])/seconds,
                      pictures_hz=(last['pictures']-first['pictures'])/seconds,
                      expected_world_hz=RATES[speed])
        (out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
        assert first['active'] == 1 and last['active'] == 1, 'measurement left the flight loop'
        assert first['rate'] == RATES[speed] and first['flight_rate'] == RATES[speed], 'world rate not selected'
        assert first['framerate'] == framerate, 'framerate option not selected'
        if not framerate:
            assert last['pictures']-first['pictures'] <= last['ticks']-first['ticks']+1, 'more pictures than world ticks'
    finally:
        stop()


def bolts(a, cmd, until, var, names, sb, sy, a4, v, ocs, slave, out):
    def values(addr, n, f):
        r = cmd(f'x/{n}{f} {addr:#x}')
        return [int(x) for line in r.splitlines() if ':' in line for x in line.split(':', 1)[1].split()]
    hz, rate = var(names['hz']), var('timing_world_rate')
    cls, pos, vel = (a4+v.A4[k] for k in ('object_class', 'position', 'velocity'))
    owner = a4+(0x3058 if ocs else 0x3a6a)      # native shooter byte; zero is the player
    rows = []
    cmd('monitor key 40 1')
    for _ in range(a.bolts):
        until(sb+sy['timing_scene_end'])            # staged poses are still in place
        c, o = values(cls, 61, 'dh'), values(owner, 61, 'db')
        p, w = values(pos, 183, 'dw'), values(vel, 183, 'dw')
        rows.append(dict(render=values(sb+sy['release_render_time'], 4, 'dw'),
                         bolts={s: (p[s*3:s*3+3], w[s*3:s*3+3]) for s in range(10, 61) if c[s] == 8 and o[s] == 0}))
    cmd('monitor key 40 0')
    bound, ratios, bounded = hz+2*rate, [], 0
    for x, y in zip(rows, rows[1:]):
        dt = y['render'][0]-x['render'][0]
        if dt <= 0:
            continue
        if bound in (x['render'][3], y['render'][3]):
            bounded += 1
            continue
        for s, (p0, w0) in x['bolts'].items():
            if s not in y['bolts'] or y['bolts'][s][1] != w0 or not any(w0):
                continue
            step = sum((q-r)*k for r, q, k in zip(p0, y['bolts'][s][0], w0))/sum(k*k for k in w0)
            if 0 <= step <= 3:                      # larger or negative: the slot was reused
                ratios.append(step/dt*hz/rate)
    result = dict(variant=a.variant, setup=a.setup, custom5=a.custom5, scene='bolts', pictures=len(rows),
                  slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(), hz=hz, rate=rate,
                  steps=len(ratios), bounded_pairs=bounded,
                  speed_min=min(ratios, default=None), speed_max=max(ratios, default=None))
    (out/'report.json').write_text(json.dumps(dict(result, rows=rows))+'\n')
    print(json.dumps(result))
    assert len(ratios) >= a.bolts, 'too few bolt steps'
    assert all(abs(r-1) < 0.02 for r in ratios), 'uneven bolt motion'


if __name__ == '__main__':
    main()
