#!/usr/bin/env python3
"""FR7 builds (FASTRAM_PLAN.md FR7) from the working tree.

  fr7_build.py [TAG]   tmp/build/fr7-production  production (asserts the reference sha)
                       tmp/build/fr7-TAG         FF1_FINE_DEFINES=FF1_FAST_RENDER=1 (default TAG candidate):
                                                 copy mode 2, the displayed region compared with the view mirror
                       tmp/build/fr7-TAG-copy1   FF1FastRenderCopy 2 -> 1: the displayed region of the dirty rows
                       tmp/build/fr7-TAG-copy0   FF1FastRenderCopy 2 -> 0: FR6, every dirty row whole
The arms differ from the candidate only in the preset word, so all three share one layout.
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
    subprocess.run([sys.executable, str(BUILD), '--game', str(GAME), '--out', str(out)], check=True, env=env,
                   stdout=subprocess.DEVNULL)
    return out


sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tag = sys.argv[1] if len(sys.argv) > 1 else 'candidate'
prod = build('fr7-production')
assert sha(prod / 'FerrariFormulaOne.slave') == PRODUCTION_SHA, 'production slave changed'
cand = build(f'fr7-{tag}', 'FF1_FAST_RENDER=1')
m = json.loads((cand / 'build.json').read_text())
pm = json.loads((prod / 'build.json').read_text())
assert all(m['payloads'][k]['sha256'] == pm['payloads'][k]['sha256'] for k in ('000', '020')), 'coarse payloads changed'
print(f'fr7-{tag}', sha(cand / 'FerrariFormulaOne.slave'))
at = 32 + m['payloads']['fine']['offset'] + m['payloads']['fine']['symbols']['FF1FastRenderCopy']
for mode in (1, 0):
    arm = r / f'tmp/build/fr7-{tag}-copy{mode}'
    if arm.exists():
        shutil.rmtree(arm)
    shutil.copytree(cand, arm)
    d = bytearray((arm / 'FerrariFormulaOne.slave').read_bytes())
    assert d[at:at + 2] == bytes((0, 2))
    d[at:at + 2] = bytes((0, mode))
    (arm / 'FerrariFormulaOne.slave').write_bytes(d)
    print(arm.name, sha(arm / 'FerrariFormulaOne.slave'))
