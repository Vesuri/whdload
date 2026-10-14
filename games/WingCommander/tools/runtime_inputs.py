#!/usr/bin/env python3
"""Prepare fresh runtime drives from the explicitly selected pinned archive, below tmp/."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def prepare(out, variant="cd32"):
    if variant not in ("cd32", "ocs"):
        raise ValueError("variant must be cd32 or ocs")
    out = out.resolve()
    if (ROOT/'tmp').resolve() not in out.parents:
        raise ValueError('runtime output must be below tmp/')
    rows = [line.split('\t') for line in (ROOT/'manifest/inputs.tsv').read_text().splitlines()
            if line.startswith(variant+'\t')]
    _, filename, expected, _ = rows[0]
    archive = ROOT/'tmp/downloads'/filename
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError(variant+' archive checksum mismatch')
    dh0, dh1 = out/'dh0', out/'dh1'
    dh1.mkdir()  # existing drives are never overwritten
    subprocess.run(['lha', 'xq', str(archive)], cwd=dh1, check=True)
    game = dh1/('WingCommanderCD32' if variant == 'cd32' else 'WingCommander')
    (dh0/'s').mkdir(parents=True)
    kicks = dh0/'devs/Kickstarts'
    kicks.mkdir(parents=True)
    rom = Path(os.environ['KICKSTART_A1200' if variant == 'cd32' else 'KICKSTART13'])
    kickname = 'kick40068.A1200' if variant == 'cd32' else 'kick34005.A500'
    rtb = os.environ.get('RTB_A1200' if variant == 'cd32' else 'RTB', str(rom)+'.RTB')
    shutil.copyfile(rom, kicks/kickname)
    shutil.copyfile(rtb, kicks/(kickname+'.RTB'))
    shutil.copyfile(os.environ['WHDLOAD_BINARY'], game/'WHDLoad')
    if os.environ.get('SLAVE'):
        # Keep the archive's original alongside the selected build.
        target = game/(game.name+'.Slave')
        target.rename(game/(game.name+'.original'))
        shutil.copyfile(os.environ['SLAVE'], target)
        if variant == 'ocs' and b'C5:B:Enhanced framerate (68020+Fast RAM);' in target.read_bytes():
            from ocs_icon import enhanced_icon
            icon = game/'WingCommander.info'
            icon.write_bytes(enhanced_icon(icon.read_bytes()))
    print('fresh boot drives:', out.relative_to(ROOT))

if __name__ == '__main__':
    prepare(Path(sys.argv[1]), os.environ.get("WC_VARIANT", "cd32"))
