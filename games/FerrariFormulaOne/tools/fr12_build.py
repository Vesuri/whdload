#!/usr/bin/env python3
"""FR12 builds (FASTRAM_PLAN.md FR12, draw speed) from the working tree.

  fr12_build.py [TAG] [--scenes]
    tmp/build/fr12-production   production (asserts the reference sha)
    tmp/build/fr12-TAG          FF1_FINE_DEFINES=FF1_FAST_RENDER=1 (default TAG candidate)
    tmp/build/fr12-TAG-pace     plus FF1_FAST_RENDER_PACING=1 (tools/fr8_report.py reads it)
  --scenes: also the pacing build's normal, solo, grid and dense fixtures through
  tools/fr0_build.py's matched builders: tmp/build/fr12-TAG-pace-{normal,solo,grid,dense}.
Every build X gets the arms X-early0 (FF1FastRenderEarly 1 -> 0, FR8) and X-merge0
(FF1FastRenderMerge 1 -> 0: the native car blits); the arms share X's layout.
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

r = Path(__file__).resolve().parents[1]
BUILD = r / 'tools/build.py'
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'
PRODUCTION_SHA = '9008bdb0ce780cfbaed1bbb891e4a7117e101d273d8adf7c710fdf6be78fb0cb'
FR = 'FF1_FAST_RENDER=1'
PACE = FR + ',FF1_FAST_RENDER_PACING=1'
ARMS = {'early0': 'FF1FastRenderEarly', 'merge0': 'FF1FastRenderMerge'}


def build(tag, defines=''):
    out = r / f'tmp/build/{tag}'
    env = dict(os.environ); env.pop('FF1_FINE_DEFINES', None)
    if defines:
        env['FF1_FINE_DEFINES'] = defines
    subprocess.run([sys.executable, str(BUILD), '--game', str(GAME), '--out', str(out)], check=True, env=env,
                   stdout=subprocess.DEVNULL)
    return out


sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def arm(out, name):
    """A copy of build OUT with the preset of arm NAME patched 1 -> 0."""
    m = json.loads((out / 'build.json').read_text())
    at = 32 + m['payloads']['fine']['offset'] + m['payloads']['fine']['symbols'][ARMS[name]]
    dst = out.parent / f'{out.name}-{name}'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(out, dst)
    d = bytearray((dst / 'FerrariFormulaOne.slave').read_bytes())
    assert d[at:at + 2] == bytes((0, 1))
    d[at:at + 2] = bytes((0, 0))
    (dst / 'FerrariFormulaOne.slave').write_bytes(d)
    print(dst.name, sha(dst / 'FerrariFormulaOne.slave'))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    tag = args[0] if args else 'candidate'
    prod = build('fr12-production')
    assert sha(prod / 'FerrariFormulaOne.slave') == PRODUCTION_SHA, 'production slave changed'
    pm = json.loads((prod / 'build.json').read_text())
    for name, defines in [(f'fr12-{tag}', FR), (f'fr12-{tag}-pace', PACE)]:
        out = build(name, defines)
        m = json.loads((out / 'build.json').read_text())
        assert all(m['payloads'][k]['sha256'] == pm['payloads'][k]['sha256'] for k in ('000', '020')), \
            'coarse payloads changed'
        print(name, sha(out / 'FerrariFormulaOne.slave'))
        for a in ARMS:
            arm(out, a)
    if '--scenes' in sys.argv:
        # fr0_build.py's 'base' variant (the unchanged source) under this tag, with the defines.
        os.environ['FF1_FINE_DEFINES'] = PACE
        src = (r / 'tools/fr0_build.py').read_text()
        old = "    tag = f'fr0-{variant}'\n"
        assert src.count(old) == 1
        g = dict(__name__='fr0_build', __file__=str(r / 'tools/fr0_build.py'))
        exec(compile(src.replace(old, f"    tag = {f'fr12-{tag}-pace'!r}\n"), 'fr0_build.py', 'exec'), g)
        g['build']('base')
        for scene in ['normal', 'solo', 'grid', 'dense']:
            for a in ARMS:
                arm(r / f'tmp/build/fr12-{tag}-pace-{scene}', a)
