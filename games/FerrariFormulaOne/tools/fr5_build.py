#!/usr/bin/env python3
"""FR5 builds (FASTRAM_PLAN.md FR5) from the working tree.

  fr5_build.py      tmp/build/fr5-production  production (asserts the reference sha)
                    tmp/build/fr5-candidate   FF1_FINE_DEFINES=FF1_FAST_RENDER=1
                                              (FR5f: the whole draw in the prefix)
                    tmp/build/fr5-fr5X        candidate with FF1FastRenderStages 6 -> 1..5
                                              (X = a..e: the prefix ends after that stage)
                    tmp/build/fr5-empty       candidate with FF1FastRenderStages 6 -> 0
                                              (empty prefix: the FR4 arm, equal layout)
                    tmp/build/fr5-control     candidate with FF1FastRenderControl 1 -> 0
                                              (the equal-layout B arm: today's path)
                    tmp/build/fr5-full        diagnostic: the whole draw redirected into
                                              the Fast shadows, the back bank published
                                              at the end of B8Draw
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

r = Path(__file__).resolve().parents[1]
BUILD = r / 'tools/build.py'
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'
PRODUCTION_SHA = '376d116419e4f7e7de2756043944658fb14d7be39dca840e4ba6407f1c4d3bd6'


def build(tag, defines=''):
    out = r / f'tmp/build/{tag}'
    env = dict(os.environ); env.pop('FF1_FINE_DEFINES', None)
    if defines:
        env['FF1_FINE_DEFINES'] = defines
    subprocess.run([sys.executable, str(BUILD), '--game', str(GAME), '--out', str(out)], check=True, env=env)
    return out


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


only = sys.argv[1:]
if not only or 'production' in only:
    prod = build('fr5-production')
    assert sha(prod / 'FerrariFormulaOne.slave') == PRODUCTION_SHA, 'production slave changed'
if not only or 'candidate' in only:
    cand = build('fr5-candidate', 'FF1_FAST_RENDER=1')
    m = json.loads((cand / 'build.json').read_text())
    arms = [('fr5-control', 'FF1FastRenderControl', 1, 0), ('fr5-empty', 'FF1FastRenderStages', 6, 0)]
    arms += [(f'fr5-fr5{x}', 'FF1FastRenderStages', 6, n) for n, x in enumerate('abcde', 1)]
    for tag, symbol, old, new in arms:
        ctl = r / f'tmp/build/{tag}'
        if ctl.exists():
            shutil.rmtree(ctl)
        shutil.copytree(cand, ctl)
        at = 32 + m['payloads']['fine']['offset'] + m['payloads']['fine']['symbols'][symbol]
        d = bytearray((ctl / 'FerrariFormulaOne.slave').read_bytes()); assert d[at:at + 2] == bytes((0, old)); d[at:at + 2] = bytes((0, new))
        (ctl / 'FerrariFormulaOne.slave').write_bytes(d)
if not only or 'full' in only:
    build('fr5-full', 'FF1_FAST_RENDER=1,FF1_FAST_RENDER_FULL=1')
if 'chipread' in only:
    build('fr5-chipread', 'FF1_FAST_RENDER=1,FF1_FAST_RENDER_FULL=1,FF1_FAST_RENDER_CHIPREAD=1')
info = {}
for t in ('fr5-production', 'fr5-candidate', *(f'fr5-fr5{x}' for x in 'abcde'), 'fr5-empty', 'fr5-control', 'fr5-full', 'fr5-chipread'):
    p = r / f'tmp/build/{t}/FerrariFormulaOne.slave'
    if p.exists():
        info[t] = sha(p)
pm = json.loads((r / 'tmp/build/fr5-production/build.json').read_text())
same = {}
for t in ('fr5-candidate', 'fr5-full', 'fr5-chipread'):
    p = r / f'tmp/build/{t}/build.json'
    if p.exists():
        m = json.loads(p.read_text())
        same[t] = {k: m['payloads'][k]['sha256'] == pm['payloads'][k]['sha256'] for k in ('000', '020')}
        assert all(same[t].values()), same
info['coarse_payloads_identical'] = same
(r / 'tmp/build/fr5-builds.json').write_text(json.dumps(info, indent=1) + '\n')
print(json.dumps(info, indent=1))
