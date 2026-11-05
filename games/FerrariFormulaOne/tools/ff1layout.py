"""The source layout from before the import, for harness scripts that copy or patch it.

Before the move into this repository the slave was Games/FerrariFormulaOne_*.s (the host
and its modules) beside Games/FerrariFormulaOne/ (the payload sources and the build
scripts). legacy() stages that view from src/ and tools/ under tmp/build/legacy-games/ and
returns its path, so a script that globs, copies and builds the old tree runs unchanged.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_FILES = ['build.py', 'bindings.py', 'native.py', 'reset.py', 'layout.json']


def stage(dest):
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    sub = dest / 'FerrariFormulaOne'
    sub.mkdir(parents=True)
    for p in sorted((ROOT / 'src').glob('*.s')):
        shutil.copy2(p, dest / p.name if p.name.startswith('FerrariFormulaOne_') else sub / p.name)
    for name in BUILD_FILES:
        shutil.copy2(ROOT / 'tools' / name, sub / name)
    return dest


def legacy():
    return stage(ROOT / 'tmp/build/legacy-games')
