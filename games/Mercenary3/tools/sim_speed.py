#!/usr/bin/env python3
"""Does game time depend on the frame rate? Drive the route on one machine and sample state.

  AMIGA_SETUP=a1200-fast python3 tools/sim_speed.py OUT.json
  python3 tools/sim_speed.py --compare A.json B.json ...
  PER_FRAME=1 AMIGA_SETUP=a500-1.5m python3 tools/sim_speed.py OUT.json
  python3 tools/sim_speed.py --frames OUT.json

Boots like route_profile.py (native FS-UAE, WARP=1, DETERMINISTIC=1, JOY0=none), stops at
the game's entry and runs its ROUTE with no tracing, reading every STEP fields (default 5):
the player position (chip $7146, $714A, $714E: longwords the walk adds velocity x elapsed
fields to), the angles at $7154/$7156, the in-game clock (bytes $57B0..$57B3; $57B3 holds the
displayed seconds), the game's frame counter ($7180) and VERTB counter
($529F4). Same input on the same fields on every machine, so equal state at equal fields
means game time runs independently of the frame rate. PER_FRAME=1 samples at every frame
publication instead, with the elapsed fields ($52954) that frame's world ticks were based on.
"""
import json
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.gdbserve import Server
from amigaxdev.input import Input
from route_profile import ENTRY, FRAME, ROOT, ROUTE

STEP = int(os.environ.get('STEP', '5'))
PER_FRAME = os.environ.get('PER_FRAME') == '1'
LONGS = {'x': 0x7146, 'y': 0x714a, 'z': 0x714e}
WORDS = {'ang1': 0x7154, 'ang2': 0x7156, 'frames': 0x7180, 'vertb': 0x529f4}


def read(g):
    out = {}
    for name, addr in LONGS.items():
        out[name] = int(g.cmd(f'x/1xw {addr:#x}').split(':')[1].split()[0], 16)
    for name, addr in WORDS.items():
        out[name] = int(g.cmd(f'x/1xh {addr:#x}').split(':')[1].split()[0], 16)
    out['clock'] = [int(v, 16) for v in g.cmd('x/4xb 0x57b0').split(':')[1].split()]
    for name in ('x', 'y', 'z'):
        out[name] -= (out[name] & 0x80000000) << 1
    return out


def run(path):
    setup = os.environ.get('AMIGA_SETUP', 'a1200-fast')
    os.environ.update(AMIGA_SETUP=setup, WARP='1', DETERMINISTIC='1', JOY0='none',
                      FSUAE=os.environ.get('FSUAE') or os.environ['FSUAE_ARM'])
    os.chdir(ROOT)
    server = Server('merc3', root=ROOT, profile_window=False)
    g = server.boot()
    samples, field = [], 0
    try:
        g.cmd(f'break *{ENTRY:#x}')
        g.cmd('continue', timeout=600)
        g.cmd('delete')
        samples.append(dict(field=0, **read(g)))
        with Input(g) as controls:
            for fields, held in ROUTE:
                for name in held:
                    controls.button(name, True)
                if PER_FRAME:
                    # Stop at every frame until the segment's fields have run (the last frame
                    # can overshoot the segment by less than one frame).
                    start = read(g)['vertb']
                    g.cmd(f'break *{FRAME:#x}')
                    while True:
                        g.cmd('continue', timeout=600)
                        s = read(g)
                        elapsed = (s['vertb'] - start) & 0xffff
                        samples.append(dict(field=field + elapsed, held=held,
                                            dt=int(g.cmd('x/1dh 0x52954').split(':')[1]), **s))
                        if elapsed >= fields:
                            break
                    g.cmd('delete')
                    field += elapsed
                    for name in held:
                        controls.button(name, False)
                    continue
                left = fields
                while left:
                    n = min(STEP, left)
                    controls.fields(n)
                    field += n
                    left -= n
                    samples.append(dict(field=field, **read(g)))
                for name in held:
                    controls.button(name, False)
    finally:
        g.p.kill()
        pid = open(os.path.join(server.run_dir, 'fsuae.pid')).read().strip()
        if 'fs-uae' in subprocess.run(['ps', '-o', 'comm=', '-p', pid], capture_output=True,
                                      text=True).stdout:
            os.kill(int(pid), signal.SIGKILL)
    json.dump(dict(setup=setup, route=ROUTE, step=STEP, per_frame=PER_FRAME, samples=samples),
              open(path, 'w'))
    print('wrote', path)


def frames(path):
    """Per-frame motion against the elapsed fields ($52954) the frame was published after."""
    r = json.load(open(path))
    print(f'{r["setup"]}: per frame, held input, fields since the previous frame, motion')
    prev = None
    for s in r['samples']:
        if prev and 'dt' in s and prev.get('held') == s['held']:
            print(f'  field {s["field"]:4} {"+".join(s["held"]) or "-":10} dt {s["dt"]:2}  '
                  f'dz {s["z"] - prev["z"]:5}  dheading {(s["ang2"] - prev["ang2"]) & 0x3ff:4}')
        prev = s


def compare(paths):
    runs = [json.load(open(p)) for p in paths]
    by = [{s['field']: s for s in r['samples']} for r in runs]
    common = sorted(set(by[0]).intersection(*by[1:]))
    print('field  ' + '  '.join(f'{r["setup"]:>44}' for r in runs))
    print('       ' + '  '.join(f'{"frames":>6} {"z":>9} {"heading":>7} {"clock":>11} {"vertb":>5}'
                                for _ in runs))
    for f in common:
        if f % 25:
            continue
        print(f'{f:5}  ' + '  '.join(
            f'{b[f]["frames"] - b[0]["frames"]:6} {b[f]["z"]:9} {b[f]["ang2"]:7} '
            f'{"".join(f"{v:02x}" for v in b[f]["clock"]):>11} '
            f'{(b[f]["vertb"] - b[0]["vertb"]) & 0xffff:5}' for b in by))
    # Rates per route segment, per emulated second (50 fields).
    edges, f = [0], 0
    for n, _ in runs[0]['route']:
        f += n
        edges.append(f)
    print()
    for k, (a, e) in enumerate(zip(edges, edges[1:])):
        held = '+'.join(runs[0]['route'][k][1]) or 'no input'
        print(f'fields {a}-{e} ({held}), per second:')
        for r, b in zip(runs, by):
            s0, s1, sec = b[a], b[e], (e - a) / 50
            print(f'  {r["setup"]:12} {(s1["frames"] - s0["frames"]) / sec:6.2f} fps  '
                  f'z {(s1["z"] - s0["z"]) / sec:9.1f}  heading {(s1["ang2"] - s0["ang2"]) / sec:7.1f}  '
                  f'clock seconds {(s1["clock"][3] - s0["clock"][3]) / sec:5.2f}')


if __name__ == '__main__':
    if sys.argv[1:2] == ['--compare']:
        compare(sys.argv[2:])
    elif sys.argv[1:2] == ['--frames']:
        frames(sys.argv[2])
    elif len(sys.argv) == 2:
        run(os.path.abspath(sys.argv[1]))
    else:
        sys.exit(__doc__)
