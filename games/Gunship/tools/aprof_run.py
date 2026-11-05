#!/usr/bin/env python3
"""Exact per-PC cycle profile of flight_profile's window on any CPU: aprof_run.py OUT

MACHINE=a1200-030 etc. (gunship.MACHINES). Uses AmigaXDev's aprof FS-UAE plus
patches/fsuae-aprof-mouse.patch ($AMIGA_SHARE/fs-uae-aprof-mouse; GUNSHIP_FSUAE overrides).
Replays the route, then `monitor aprof start`, the window (same keys on the same fields),
`monitor aprof stop OUT/window.prof`, and an end screenshot. Summarise with
aprof_report.py OUT/window.prof OUT.
"""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('GUNSHIP_FSUAE',os.path.join(os.environ['AMIGA_SHARE'],'fs-uae-aprof-mouse/fs-uae'))
from gunship import Session
from route import run
from flight_profile import ROUTE,window
import json
from layout import locate
# Game clocks (timemodel.md) as (hunk, offset, size): VBL counter (VBL server), simulation tick,
# altitude. The layout moves with the CPU (WHDLoad allocates differently), so it is located in a
# fast-RAM dump taken at the window start; OUT then doubles as the MEMDIR for the reports.
CLOCKS=dict(vbl=(2,0x1c,4),tick=(6,0x3b94,2),alt=(6,0x3ba4,2))
def clocks(s,L):return {k:int.from_bytes(s.read(L['hunks'][h]+o,n),'big') for k,(h,o,n) in CLOCKS.items()}
out=sys.argv[1];s=Session(out)
try:
    run(s,ROUTE);s.shot('start.png')
    mem=s.read(0x200000,0x800000);(s.out/'fast.bin').write_bytes(mem)
    L=locate(mem);json.dump(L,open(s.out/'layout.json','w'));c0=clocks(s,L)
    print(s.cmd('monitor aprof start'),flush=True)
    window(s,s.fields)
    print(s.cmd(f'monitor aprof stop {(s.out/"window.prof").resolve()}',timeout=600),flush=True)
    c1=clocks(s,L);s.shot('end.png')
    (s.out/'clocks.txt').write_text(f'start {c0}\nend {c1}\n');print('clocks',c0,c1,flush=True)
finally:s.quit()
