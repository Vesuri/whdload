#!/usr/bin/env python3
"""FR2 builds (FASTRAM_PLAN.md FR2).

  fr2_build.py production     production slave from the working tree; must equal
                              the reference sha (FastRenderBlit.s is not included)
  fr2_build.py oracle         tmp/build/fr2-oracle-normal: FF1_FAST_RENDER plus the
                              tools/fr2_oracle.s fixture in place of the drawing
                              stages (FR0's no-draw cut), cases from
                              tmp/build/fr2-data (tools/fr2_cases.py)
"""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

r = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(r / 'tools'))
from ff1layout import legacy
GAMES = legacy()
GAME = r / 'tmp/game/FerrariFormulaOne/data/racemenu'
PRODUCTION_SHA = '9008bdb0ce780cfbaed1bbb891e4a7117e101d273d8adf7c710fdf6be78fb0cb'


def source(tag):
    src = r / f'tmp/build/{tag}-source'
    if src.exists():
        shutil.rmtree(src)
    src.mkdir(parents=True)
    for p in GAMES.glob('FerrariFormulaOne_*.s'):
        shutil.copy2(p, src / p.name)
    shutil.copytree(GAMES / 'FerrariFormulaOne', src / 'FerrariFormulaOne',
                    ignore=shutil.ignore_patterns('__pycache__', '*.md'))
    return src


def oracle(src):
    p = src / 'FerrariFormulaOne_FullPresentation.s'; s = p.read_text()
    # FR3 added the publication hook after the label; the oracle runs before it.
    old = 'B8_65734:\n IFD FF1_FAST_RENDER\n bsr.l FF1FastRenderPublish\n ENDC\n jsr $6b050.l\n'; assert s.count(old) == 1
    s = s.replace(old, 'B8_65734:\n IFD FF1_FINE_ROAD_PREFETCH\n movea.l #$66c92,a0\n bsr.l FR2Oracle\n'
                  ' bra.w FR0Skip\n ENDC\n' + old[len('B8_65734:\n'):])
    old = ' jsr $2a130\n jsr $2a270\n clr.w $1c1b4\n jsr $6694e\n jsr $2a130\n'; assert s.count(old) == 1
    s = s.replace(old, '; FR2 oracle: drawing skipped; instruments are drawing too.\n'
                  ' jsr $2a130\nFR0Skip:\n jsr $2a130\n jsr $2a270\n clr.w $1c1b4\n jsr $2a130\n')
    p.write_text(s)
    f = src / 'FerrariFormulaOne/Fine.s'; t = f.read_text()
    t = 'FF1_FAST_RENDER equ 1\n' + t + ' include "FR2Oracle.s"\n'
    f.write_text(t)
    shutil.copy(r / 'tools/fr2_oracle.s', src / 'FerrariFormulaOne/FR2Oracle.s')
    shutil.copy(r / 'tmp/build/fr2-data/FR2Cases.bin', src / 'FerrariFormulaOne/FR2Cases.bin')
    if os.environ.get('FR2_FAULT') == 'ife':
        # Negative control: inclusive fill treated as exclusive.
        f = src / 'FerrariFormulaOne/FastRenderBlit.s'; t = f.read_text()
        assert t.count(' cmpi.w #$08,d4\n') == 1
        f.write_text(t.replace(' cmpi.w #$08,d4\n', ' cmpi.w #$18,d4\n'))


def build(kind):
    tag = f'fr2-{kind}' + ('-fault-' + os.environ['FR2_FAULT'] if os.environ.get('FR2_FAULT') else '')
    src = source(tag)
    if kind == 'oracle':
        oracle(src)
    out = r / f'tmp/build/{tag}-normal'
    subprocess.run([sys.executable, str(src / 'FerrariFormulaOne/build.py'), '--game', str(GAME), '--out', str(out)], check=True)
    sha = hashlib.sha256((out / 'FerrariFormulaOne.slave').read_bytes()).hexdigest()
    if kind == 'production':
        assert sha == PRODUCTION_SHA, ('production slave changed', sha)
    print(tag, sha)
    return sha


if __name__ == '__main__':
    for k in sys.argv[1:]:
        assert k in ('production', 'oracle'), k
        build(k)
