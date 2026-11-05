#!/usr/bin/env python3
"""FR0 diagnostic builds (FASTRAM_PLAN.md FR0). Test-only, never production.

  fr0_build.py VARIANT [VARIANT...]     VARIANT in base, nodraw, bench

From the working tree: tmp/build/fr0-<V>-normal (production layout plus the
variant patch) and the H5-style matched solo/grid/dense fixtures
tmp/build/fr0-<V>-{solo,grid,dense}.
  base    unchanged source (FR0b runs it with immediate blits)
  nodraw  B8Draw skips every drawing stage after the line-256 wait, the HUD,
          clock and instruments; publication, road preparation and
          Own/DisownBlitter remain (FR0a)
  bench   nodraw plus tools/fr0_bench.s copy and kernel benchmarks (FR0c/d)
"""
from pathlib import Path
import os, re, json, shutil, struct, subprocess, sys, hashlib

r = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(r / 'tools'))
from ff1layout import legacy
GAMES = legacy()
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'


def patch(src, variant):
    if variant == 'base':
        return
    p = src / 'FerrariFormulaOne_FullPresentation.s'; s = p.read_text()
    old = 'B8_65734:\n jsr $6b050.l\n'; assert s.count(old) == 1
    # FullPresentation is shared with the coarse payloads; patch the fine one only.
    call = {'bench': ' bsr.l FR0BenchLate\n', 'replay': ' bsr.l FR0Replay\n'}.get(variant, '')
    jump = ' IFD FF1_FINE_ROAD_PREFETCH\n' + call + ' bra.w FR0Skip\n ENDC\n'
    s = s.replace(old, 'B8_65734:\n' + jump + ' jsr $6b050.l\n')
    old = ' jsr $2a130\n jsr $2a270\n clr.w $1c1b4\n jsr $6694e\n jsr $2a130\n'; assert s.count(old) == 1
    s = s.replace(old, '; FR0: drawing skipped; instruments are drawing too.\n'
                  ' jsr $2a130\nFR0Skip:\n jsr $2a130\n jsr $2a270\n clr.w $1c1b4\n jsr $2a130\n')
    if variant == 'bench':
        old = 'B8_65728:\n IFD FF1_FINE_ROAD_PREFETCH\n'; assert s.count(old) == 1
        s = s.replace(old, ' IFD FF1_FINE_ROAD_PREFETCH\n bsr.l FR0BenchEarly\n ENDC\n' + old)
        f = src / 'FerrariFormulaOne/Fine.s'; t = f.read_text()
        old = ' include "RenderBlit.s"'; assert t.count(old) == 1
        f.write_text(t.replace(old, old + '\n include "FR0Bench.s"'))
        shutil.copy(r / 'tools/fr0_bench.s', src / 'FerrariFormulaOne/FR0Bench.s')
        shutil.copy(r / 'tools/fr0_bench_data.s', src / 'FerrariFormulaOne/FR0BenchData.s')
        f.write_text(f.read_text() + ' include "FR0BenchData.s"\n')
    if variant == 'replay':
        f = src / 'FerrariFormulaOne/Fine.s'
        f.write_text(f.read_text() + ' include "FR0Replay.s"\n include "FR0ReplayData.s"\n')
        shutil.copy(r / 'tools/fr0_replay.s', src / 'FerrariFormulaOne/FR0Replay.s')
        shutil.copy(r / 'tools/fr0_replay_data.s', src / 'FerrariFormulaOne/FR0ReplayData.s')
        for n in ['FR0Blob.bin', 'FR0BlitTab.bin', 'FR0FillTab.bin']:
            shutil.copy(r / 'tmp/build/fr0-replay-data' / n, src / 'FerrariFormulaOne' / n)
    p.write_text(s)


def build(variant):
    tag = f'fr0-{variant}'
    src = r / f'tmp/build/{tag}-source'
    if src.exists():
        shutil.rmtree(src)
    src.mkdir(parents=True)
    for p in GAMES.glob('FerrariFormulaOne_*.s'):
        shutil.copy2(p, src / p.name)
    shutil.copytree(GAMES / 'FerrariFormulaOne', src / 'FerrariFormulaOne',
                    ignore=shutil.ignore_patterns('__pycache__', '*.md'))
    patch(src, variant)
    subprocess.run([sys.executable, str(src / 'FerrariFormulaOne/build.py'), '--game', str(GAME),
                    '--out', str(r / f'tmp/build/{tag}-normal')], check=True)
    # Matched source and fixtures through the historical builders, retargeted.
    os.chdir(r)
    g = dict(__name__='__main__', __file__=str(r / 'tools/build_drive_matched.py'))
    s = (r / 'tools/build_drive_matched.py').read_text()
    s = s.replace("g=legacy()", f"g=Path({str(src)!r})").replace('drive-matched', f'{tag}-matched')
    assert f"g=Path({str(src)!r})" in s
    exec(compile(s, 'build_drive_matched.py', 'exec'), g)
    s = (r / 'tools/build_hi25_fixtures.py').read_text()
    s = s.replace('render-h5-matched-source', f'{tag}-matched-source').replace('render-hi25-', f'{tag}-')
    old_argv = sys.argv
    sys.argv = ['build_hi25_fixtures.py', 'solo', 'grid', 'dense']
    g = dict(__name__='__main__', __file__=str(r / 'tools/build_hi25_fixtures.py'))
    exec(compile(s, 'build_hi25_fixtures.py', 'exec'), g)
    sys.argv = old_argv
    out = {}
    for scene in ['normal', 'solo', 'grid', 'dense']:
        b = r / f'tmp/build/{tag}-{scene}/FerrariFormulaOne.slave'
        out[scene] = hashlib.sha256(b.read_bytes()).hexdigest()
    print(tag, json.dumps(out, indent=1))
    return out


if __name__ == '__main__':
    for v in sys.argv[1:]:
        assert v in ('base', 'nodraw', 'bench', 'replay'), v
        build(v)
