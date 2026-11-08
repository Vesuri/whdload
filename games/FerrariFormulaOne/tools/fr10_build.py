#!/usr/bin/env python3
"""FR10 builds (FASTRAM_PLAN.md FR10, checkpoint and release) from the working tree.

  fr10_build.py [--scenes]
    tmp/build/fr10-production       the production slave (Fast RAM rendering built in)
    tmp/build/fr10-production-off   the same bytes with FF1FastRenderControl 1 -> 0:
                                    today's path, the same layout (the FR selection gate's control)
  --scenes: also the normal, solo, grid and dense fixtures of the same source through
  tools/fr0_build.py's matched builders, tmp/build/fr10-{normal,solo,grid,dense}, each with
  its -off arm.
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

r = Path(__file__).resolve().parents[1]
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def off(out):
    """A copy of build OUT with FF1FastRenderControl patched 1 -> 0."""
    m = json.loads((out / 'build.json').read_text())
    at = 32 + m['payloads']['fine']['offset'] + m['payloads']['fine']['symbols']['FF1FastRenderControl']
    dst = out.parent / f'{out.name}-off'
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(out, dst)
    d = bytearray((dst / 'FerrariFormulaOne.slave').read_bytes())
    assert d[at:at + 2] == bytes((0, 1))
    d[at:at + 2] = bytes((0, 0))
    (dst / 'FerrariFormulaOne.slave').write_bytes(d)
    print(dst.name, sha(dst / 'FerrariFormulaOne.slave'))


if __name__ == '__main__':
    os.environ.pop('FF1_FINE_DEFINES', None)
    out = r / 'tmp/build/fr10-production'
    subprocess.run([sys.executable, str(r / 'tools/build.py'), '--game', str(GAME), '--out', str(out)], check=True,
                   stdout=subprocess.DEVNULL)
    print(out.name, sha(out / 'FerrariFormulaOne.slave'))
    off(out)
    if '--scenes' in sys.argv:
        # fr0_build.py's 'base' variant (the unchanged source) under the fr10 tag.
        src = (r / 'tools/fr0_build.py').read_text()
        old = "    tag = f'fr0-{variant}'\n"
        assert src.count(old) == 1
        g = dict(__name__='fr0_build', __file__=str(r / 'tools/fr0_build.py'))
        exec(compile(src.replace(old, "    tag = 'fr10'\n"), 'fr0_build.py', 'exec'), g)
        g['build']('base')
        assert sha(r / 'tmp/build/fr10-normal/FerrariFormulaOne.slave') == sha(out / 'FerrariFormulaOne.slave')
        for scene in ['normal', 'solo', 'grid', 'dense']:
            off(r / f'tmp/build/fr10-{scene}')
