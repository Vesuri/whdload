#!/usr/bin/env python3
"""FR6 builds (FASTRAM_PLAN.md FR6) from the working tree.

  fr6_build.py [TAG]   tmp/build/fr6-production  production (asserts the reference sha)
                       tmp/build/fr6-TAG         FF1_FINE_DEFINES=FF1_FAST_RENDER=1 (default TAG candidate)
"""
from pathlib import Path
import hashlib, json, os, subprocess, sys

r = Path(__file__).resolve().parents[1]
BUILD = r / 'tools/build.py'
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'
PRODUCTION_SHA = '597a74b9fd9a9e67bf317de1f02395d771fbc12bd6ee047e83f8630c2a4189f6'


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
prod = build('fr6-production')
assert sha(prod / 'FerrariFormulaOne.slave') == PRODUCTION_SHA, 'production slave changed'
cand = build(f'fr6-{tag}', 'FF1_FAST_RENDER=1')
print(f'fr6-{tag}', sha(cand / 'FerrariFormulaOne.slave'))
