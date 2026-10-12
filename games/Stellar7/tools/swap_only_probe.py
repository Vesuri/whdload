#!/usr/bin/env python3
"""Build a scratch-only presentation ceiling diagnostic, never a playable slave.

SWAP_ONLY replaces the native full render call with its presentation entry.
Simulation and native buffer handoff remain; pixels are deliberately stale.
Compare field/counter results with the matched --control build. Both arms
retain identical layout and differ only in one branch word. Not a visual test.
"""
import argparse
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent.parent


def build(prefix, flags, swap_only=True):
    prefix=prefix.resolve();prefix.relative_to(ROOT/'tmp');prefix.parent.mkdir(parents=True,exist_ok=True)
    relative=lambda p:os.path.relpath(p,ROOT/'whdload')
    draw=(ROOT/'whdload/draw60.s').read_text()
    assert draw.count('        S60_CALL $2bb4')==1
    draw=draw.replace('        S60_CALL $2bb4','        bsr s60_swap_probe')
    draw+='''
; Both arms include the same wrapper and preserve all code placement.
; Only this two-byte instruction differs between control and bypass.
s60_swap_probe:
        IFNE SWAP_ONLY
        bra.s .swap
        ELSE
        nop
        ENDC
        S60_CALL $2bb4
        rts
.swap:
        move.b ($1e52-S60_DATA,a4),d0
        ext.w d0
        move.w d0,-(sp)
        S60_CALL $6a0a
        IFNE BUFFER_REUSE
        ; The bypass also needs native $2c1a's field store for the draw guard.
        move.l ($24a8-S60_DATA,a4),(-22,a5)
        ENDC
        addq.l #2,sp
        rts
'''
    drawpath=prefix.with_suffix('.draw.s');drawpath.write_text(draw)
    sim=(ROOT/'whdload/sim60.s').read_text()
    assert sim.count('INCLUDE draw60.s')==1
    sim=sim.replace('INCLUDE draw60.s',f'INCLUDE "{relative(drawpath)}"')
    simpath=prefix.with_suffix('.sim.s');simpath.write_text(sim)
    source=(ROOT/'whdload/Stellar7.s').read_text()
    assert source.count('INCLUDE sim60.s')==1
    source=source.replace('INCLUDE sim60.s',f'INCLUDE "{relative(simpath)}"')
    src=prefix.with_suffix('.s');src.write_text(source)
    command=[os.environ['VASM'],'-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-DSIM60=1','-DVERIFY=1','-DS60_SUBSTEPS=12',f'-DSWAP_ONLY={int(swap_only)}',*flags,'-I.','-Iinclude','-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['NDK'],'-L',relative(prefix.with_suffix('.lst')),'-o',relative(prefix.with_suffix('.slave')),relative(src)]
    with prefix.with_suffix('.log').open('w') as log:subprocess.run(command,cwd=ROOT/'whdload',stdout=log,stderr=subprocess.STDOUT,check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path)
    p.add_argument('--define',action='append',default=[],help='additional fixture NAME=VALUE')
    p.add_argument('--control',action='store_true',help='same-layout full-render control, differing only in the branch word')
    a=p.parse_args();build(a.prefix,['-D'+s for s in a.define],not a.control)
