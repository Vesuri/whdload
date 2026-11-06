#!/usr/bin/env python3
"""FR3 builds (FASTRAM_PLAN.md FR3) from the working tree.

  fr3_build.py      tmp/build/fr3-production  production (asserts the reference sha)
                    tmp/build/fr3-candidate   FF1_FINE_DEFINES=FF1_FAST_RENDER=1
                    tmp/build/fr3-control     candidate with FF1FastRenderControl 1 -> 0
                                              (the equal-layout B arm: today's path)
                    tmp/build/fr3-roundtrip   diagnostic: every publish refreshes the
                                              back shadow and copies the 24,000-byte
                                              region back to Chip (bank must not change)
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

r = Path(__file__).resolve().parents[1]
BUILD = r / 'tools/build.py'
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'
PRODUCTION_SHA = '9008bdb0ce780cfbaed1bbb891e4a7117e101d273d8adf7c710fdf6be78fb0cb'


def build(tag, defines=''):
    out = r / f'tmp/build/{tag}'
    env = dict(os.environ); env.pop('FF1_FINE_DEFINES', None)
    if defines:
        env['FF1_FINE_DEFINES'] = defines
    subprocess.run([sys.executable, str(BUILD), '--game', str(GAME), '--out', str(out)], check=True, env=env)
    return out


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


prod = build('fr3-production')
assert sha(prod / 'FerrariFormulaOne.slave') == PRODUCTION_SHA, 'production slave changed'
cand = build('fr3-candidate', 'FF1_FAST_RENDER=1')
ctl = r / 'tmp/build/fr3-control'
if ctl.exists():
    shutil.rmtree(ctl)
shutil.copytree(cand, ctl)
m = json.loads((cand / 'build.json').read_text())
at = 32 + m['payloads']['fine']['offset'] + m['payloads']['fine']['symbols']['FF1FastRenderControl']
d = bytearray((ctl / 'FerrariFormulaOne.slave').read_bytes()); assert d[at:at + 2] == b'\0\1'; d[at:at + 2] = b'\0\0'
(ctl / 'FerrariFormulaOne.slave').write_bytes(d)
rt = build('fr3-roundtrip', 'FF1_FAST_RENDER=1,FF1_FAST_RENDER_ROUNDTRIP=1')
pm = json.loads((prod / 'build.json').read_text())
same = {k: m['payloads'][k]['sha256'] == pm['payloads'][k]['sha256'] for k in ('000', '020')}
assert all(same.values()), same
info = {t: sha(r / f'tmp/build/{t}/FerrariFormulaOne.slave') for t in ('fr3-production', 'fr3-candidate', 'fr3-control', 'fr3-roundtrip')}
info['coarse_payloads_identical'] = same
(r / 'tmp/build/fr3-builds.json').write_text(json.dumps(info, indent=1) + '\n')
print(json.dumps(info, indent=1))
