#!/usr/bin/env python3
"""Prepare fresh runtime drives from the pinned CD32 archive, below tmp/."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def prepare(out):
    out = out.resolve()
    if (ROOT/'tmp').resolve() not in out.parents:
        raise ValueError('runtime output must be below tmp/')
    rows = [line.split('\t') for line in (ROOT/'manifest/inputs.tsv').read_text().splitlines()
            if line.startswith('cd32\t')]
    _, filename, expected, _ = rows[0]
    archive = ROOT/'tmp/downloads'/filename
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError('CD32 archive checksum mismatch')
    dh0, dh1 = out/'dh0', out/'dh1'
    dh1.mkdir()  # existing drives are never overwritten
    subprocess.run(['lha', 'xq', str(archive)], cwd=dh1, check=True)
    game = dh1/'WingCommanderCD32'
    (dh0/'s').mkdir(parents=True)
    kicks = dh0/'devs/Kickstarts'
    kicks.mkdir(parents=True)
    rom = Path(os.environ['KICKSTART_A1200'])
    shutil.copyfile(rom, kicks/'kick40068.A1200')
    shutil.copyfile(os.environ.get('RTB_A1200', str(rom)+'.RTB'), kicks/'kick40068.A1200.RTB')
    shutil.copyfile(os.environ['WHDLOAD_BINARY'], game/'WHDLoad')
    if os.environ.get('SLAVE'):
        # Keep the archive's original alongside the selected build.
        target = game/'WingCommanderCD32.Slave'
        target.rename(game/'WingCommanderCD32.original')
        shutil.copyfile(os.environ['SLAVE'], target)
    print('fresh boot drives:', out.relative_to(ROOT))

if __name__ == '__main__':
    prepare(Path(sys.argv[1]))
