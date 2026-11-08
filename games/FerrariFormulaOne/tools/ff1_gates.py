#!/usr/bin/env python3
"""Correctness gates for the current source against the accepted B8-PAL references.

  ff1_gates.py --build DIR --tag TAG [--skip-prepare] [CASE ...]

Prepares matched-state, grid and stable-scanout fixtures from the working tree
(tmp/build/render-<TAG>-*). Then on 040-40-bce it requires: exact 100-update
states (records.bin and private.json; only Fast pointers, moved by the 1 MiB layout, may differ), 30 frames equal to the B8-PAL frames
for the normal and grid scenes, and elapsed clock error <= 0.25% over 60
simulated seconds using DIR's slave. Writes manifest/gates-<TAG>.json.
Cases are named states/normal, frames/normal, frames/grid, timing/elapsed.
Generalizes the former prepare_cachepol.py and run_cachepol_checks.py.
"""
import argparse, gzip, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

r = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--build', required=True); ap.add_argument('--tag', required=True)
ap.add_argument('--skip-prepare', action='store_true'); ap.add_argument('cases', nargs='*')
a = ap.parse_args()
tag = a.tag.replace('/', '-')
PROFILE = '040-40-bce'
PERF = 'CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache'


def prepare():
    # Fixture builders are shared historical tools; they are retargeted by name.
    os.chdir(r)
    import re, struct
    # One shared namespace, as the sliced sections rely on earlier definitions.
    g = dict(__name__='__main__', __file__=str(r / 'tools/build_drive_matched.py'), r=r, Path=Path, re=re, json=json, shutil=shutil, subprocess=subprocess,
             sys=sys, struct=struct, os=os, hashlib=hashlib)
    s = (r / 'tools/build_drive_matched.py').read_text().replace('drive-matched', f'render-{tag}-matched')
    exec(compile(s, str(r / 'tools/build_drive_matched.py'), 'exec'), g)
    h = (r / 'tools/prepare_b8pal.py').read_text()
    exec(h[h.index('def control('):h.index("base=r/'tmp/build/render-b8pal';")], g)
    s = (r / 'tools/build_hi25_fixtures.py').read_text().replace('render-h5-matched-source', f'render-{tag}-matched-source') \
        .replace('render-hi25-', f'render-{tag}-')
    sys.argv = ['build_hi25_fixtures.py', 'grid']
    exec(compile(s, str(r / 'tools/build_hi25_fixtures.py'), 'exec'), g)
    s = (r / 'tools/build_b8pal_stable_frames.py').read_text()
    exec(compile(s[s.index('for scene in'):].replace('render-b8pal-', f'render-{tag}-'), 'stable', 'exec'), g)


def same_but_pointers(a, b):
    """A and B equal except for longs (at any word offset) that are Fast addresses in both:
    the 1 MiB ExpMem of Fast RAM rendering moves the guest's Fast allocations (FASTRAM_PLAN
    FR4, FR10). Returns the count of moved pointers per delta."""
    import collections, struct
    assert len(a) == len(b)
    fast = lambda v: 0x200000 <= v < 0xa00000
    covered, moved = set(), collections.Counter()
    for i in range(0, len(a), 2):
        if a[i:i + 2] == b[i:i + 2] or i in covered:
            continue
        for at in (i - 2, i):
            if at < 0 or at + 4 > len(a):
                continue
            x, y = struct.unpack_from('>I', a, at)[0], struct.unpack_from('>I', b, at)[0]
            if fast(x) and fast(y):
                moved[hex(x - y)] += 1; covered.update((at, at + 2)); break
        else:
            raise AssertionError(f'records differ at {i:#x}, not a Fast pointer')
    return dict(moved)


def raw(p, name):
    f = p / name
    if f.exists():
        return f.read_bytes()
    with gzip.open(p / (name + '.gz')) as z:
        return z.read()


if not a.skip_prepare:
    prepare()


def early0(b):
    # FR8 (FASTRAM_PLAN.md): the frame capture screenshots a fixed number of fields after
    # B8Draw returns, so the early LoadView request (FF1FastRenderEarly 1) shows a newer
    # frame there than the references. The frame fixtures take the preset's native arm
    # (0), which differs from the build in that word alone; the census check in
    # tools/fr8_report.py covers the early arm's display.
    j = b / 'build.json'
    if not j.exists():
        return
    m = json.loads(j.read_text())
    at = m['payloads']['fine']['symbols'].get('FF1FastRenderEarly')
    if at is None:
        return
    at += 32 + m['payloads']['fine']['offset']
    d = bytearray((b / 'FerrariFormulaOne.slave').read_bytes())
    if d[at:at + 2] == bytes((0, 1)):
        d[at:at + 2] = bytes((0, 0))
        (b / 'FerrariFormulaOne.slave').write_bytes(d)
        print('frames fixture', b.name, 'FF1FastRenderEarly 0', flush=True)


build = Path(a.build).resolve()
cases = [('states', 'state', r / f'tmp/build/render-{tag}-matched'),
         ('frames', 'normal', r / f'tmp/build/render-{tag}-matched-stable-frames'),
         ('frames', 'grid', r / f'tmp/build/render-{tag}-grid-stable-frames'),
         ('timing', 'elapsed', build)]
script = {'states': 'capture_drive_states.py', 'frames': 'capture_h7_frames.py', 'timing': 'test_h7_elapsed.py'}
prefix = {'states': 'c4-q03-drive-state-production', 'frames': 'c4-q03-h5-frame-production', 'timing': 'c4-q03-drive-timing'}
mp = r / f'tmp/manifest/gates-{tag}.json'
report = {'status': 'running', 'build': str(build), 'results': {}}
for mode, case, b in cases:
    key = f'{mode}/{case}'
    if a.cases and key not in a.cases:
        continue
    if mode == 'frames':
        early0(b)
    ctag = f'{tag}-{case}'
    env = dict(os.environ, H5_BUILD=str(b), DRIVE_MATCHED=str(b / 'FerrariFormulaOne.slave'), C1_VARIANT=ctag,
               RELEASE_WHD_ARGS=PERF)
    p = r / f'tmp/step5/{prefix[mode]}-{PROFILE}-{ctag}'
    old = r / f'tmp/step5/{prefix[mode]}-{PROFILE}-b8pal-{case}'
    log = r / f'tmp/ff1check/gate-{mode}-{case}-{tag}.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    print('RUN', key, flush=True)
    with log.open('w') as f:
        subprocess.run([sys.executable, str(r / 'tools' / script[mode]), PROFILE], env=env, stdout=f,
                       stderr=subprocess.STDOUT, check=True)
    x = json.loads((p / 'result.json').read_text())
    assert x['error'] == 0 and x['slave_sha256'] == hashlib.sha256((b / 'FerrariFormulaOne.slave').read_bytes()).hexdigest()
    if mode == 'states':
        assert x['steps'] == 100
        moved = same_but_pointers(raw(p, 'records.bin'), raw(old, 'records.bin'))
        mine, ref = json.loads((p / 'private.json').read_text()), json.loads((old / 'private.json').read_text())
        assert len(mine) == len(ref) == 100
        for m, o in zip(mine, ref):
            # wear_remainders ends in the upper word of a Fast pointer (FASTRAM_PLAN FR4).
            assert m.keys() == o.keys() and all(m[k] == o[k] for k in m if k != 'wear_remainders')
            assert m['wear_remainders'][:-4] == o['wear_remainders'][:-4]
        print('states: Fast pointers moved', moved, flush=True)
    if mode == 'frames':
        assert len(x['frames']) == 30 and x['frames'] == json.loads((old / 'result.json').read_text())['frames']
    if mode == 'timing':
        assert x['simulated_seconds'] == 60 and x['error_percent'] <= .25
        print('elapsed error %', x['error_percent'], flush=True)
    report['results'][key] = {'path': str(p.relative_to(r)), 'reference': str(old.relative_to(r)), 'error': x['error']}
    mp.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS', key, flush=True)
    for f in p.glob('*.bin'):                      # keep large captures compressed
        if f.stat().st_size < 262144:
            continue
        h = hashlib.sha256(f.read_bytes()).hexdigest(); z = f.with_suffix('.bin.gz')
        with f.open('rb') as i, gzip.open(z, 'wb', compresslevel=1) as o:
            shutil.copyfileobj(i, o)
        with gzip.open(z, 'rb') as i:
            assert hashlib.file_digest(i, 'sha256').hexdigest() == h
        f.unlink()
report['status'] = 'passed'
mp.write_text(json.dumps(report, indent=2) + '\n')
