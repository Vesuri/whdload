#!/usr/bin/env python3
"""FR8 builds (FASTRAM_PLAN.md FR8) from the working tree.

  fr8_build.py [TAG] [--scenes]
    tmp/build/fr8-production   production (asserts the reference sha)
    tmp/build/fr8-TAG          FF1_FINE_DEFINES=FF1_FAST_RENDER=1 (default TAG candidate)
    tmp/build/fr8-TAG-pace     plus FF1_FAST_RENDER_PACING=1: the per-frame pacing log
                               (src/FastRenderPacing.s; tools/fr8_report.py reads it)
  --scenes: also the pacing build's normal, solo, grid and dense fixtures through
  tools/fr0_build.py's matched builders: tmp/build/fr8-TAG-pace-{normal,solo,grid,dense}.
Every build X gets an arm X-early0 with the preset FF1FastRenderEarly 1 -> 0 (the LoadView
request left to the next B8Draw, as before FR8); the arms share X's layout.
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

r = Path(__file__).resolve().parents[1]
BUILD = r / 'tools/build.py'
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'
PRODUCTION_SHA = '376d116419e4f7e7de2756043944658fb14d7be39dca840e4ba6407f1c4d3bd6'
FR = 'FF1_FAST_RENDER=1'
PACE = FR + ',FF1_FAST_RENDER_PACING=1'


def build(tag, defines=''):
    out = r / f'tmp/build/{tag}'
    env = dict(os.environ); env.pop('FF1_FINE_DEFINES', None)
    if defines:
        env['FF1_FINE_DEFINES'] = defines
    subprocess.run([sys.executable, str(BUILD), '--game', str(GAME), '--out', str(out)], check=True, env=env,
                   stdout=subprocess.DEVNULL)
    return out


sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def early0(out):
    m = json.loads((out / 'build.json').read_text())
    at = 32 + m['payloads']['fine']['offset'] + m['payloads']['fine']['symbols']['FF1FastRenderEarly']
    arm = out.parent / (out.name + '-early0')
    if arm.exists():
        shutil.rmtree(arm)
    shutil.copytree(out, arm)
    d = bytearray((arm / 'FerrariFormulaOne.slave').read_bytes())
    assert d[at:at + 2] == bytes((0, 1))
    d[at:at + 2] = bytes((0, 0))
    (arm / 'FerrariFormulaOne.slave').write_bytes(d)
    print(arm.name, sha(arm / 'FerrariFormulaOne.slave'))


args = [a for a in sys.argv[1:] if not a.startswith('--')]
tag = args[0] if args else 'candidate'
prod = build('fr8-production')
assert sha(prod / 'FerrariFormulaOne.slave') == PRODUCTION_SHA, 'production slave changed'
pm = json.loads((prod / 'build.json').read_text())
for name, defines in [(f'fr8-{tag}', FR), (f'fr8-{tag}-pace', PACE)]:
    out = build(name, defines)
    m = json.loads((out / 'build.json').read_text())
    assert all(m['payloads'][k]['sha256'] == pm['payloads'][k]['sha256'] for k in ('000', '020')), 'coarse payloads changed'
    print(name, sha(out / 'FerrariFormulaOne.slave'))
    early0(out)
if '--scenes' in sys.argv:
    # fr0_build.py's 'base' variant (the unchanged source) under this tag, with the defines.
    os.environ['FF1_FINE_DEFINES'] = PACE
    src = (r / 'tools/fr0_build.py').read_text()
    old = "    tag = f'fr0-{variant}'\n"
    assert src.count(old) == 1
    g = dict(__name__='fr0_build', __file__=str(r / 'tools/fr0_build.py'))
    exec(compile(src.replace(old, f"    tag = {f'fr8-{tag}-pace'!r}\n"), 'fr0_build.py', 'exec'), g)
    g['build']('base')
    for scene in ['normal', 'solo', 'grid', 'dense']:
        early0(r / f'tmp/build/fr8-{tag}-pace-{scene}')
