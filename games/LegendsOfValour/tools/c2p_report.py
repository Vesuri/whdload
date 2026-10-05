#!/usr/bin/env python3
"""Completed-call C2P cycle cost, including the slave adapter (and separately interrupts).
Entry is the unchanged h12:054ce call boundary, exit is its original or slave RTS.
Exclude partial calls at the trace boundaries. Analyse with the capture's exact slave.
"""
import argparse, os, re, statistics, struct
from pathlib import Path
import barto
from lov_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--any-view',action='store_true',help='permit geometry other than the large benchmark view')
p.add_argument('--base',type=lambda x:int(x,0),default=0xc00000)
a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
t=barto.load(str(a.capture/'trace.bin'));b=(a.capture/'code.bin').read_bytes()
r={n:(lo,hi) for lo,hi,n,o in regions(b,a.base,t.chip)}
geometry=struct.unpack_from('>2H',b,r['h12'][0]-a.base+0x2e)
print(f'view geometry: {geometry[0]} x {geometry[1]}')
assert a.any_view or geometry==(192,92),'benchmark did not reach the large view'
entry=r['h12'][0]+0x54ce;ends={r['h12'][0]+0x55e6}
listing=(a.capture/'slave.lst').read_text(errors='replace')
m=re.search(r'^_c2p_return\s+00:([0-9A-F]{8})\s*$',listing,re.M)
if m:ends.add(r['slave'][0]+int(m[1],16))
active=None;calls=[];allcycles=0;changedcycles=0
for f in t.fields:
    for pc,cost,regs in t.instructions(f):
        allcycles+=cost
        if pc==entry:
            assert active is None,'nested C2P entry'
            active=[regs[15],0,0]
        if active is not None:
            active[1]+=cost
            # The main task keeps its stack in other RAM; IRQ stack is in chip.
            if abs(regs[15]-active[0]) < 0x10000:
                active[2]+=cost
            if pc in ends and regs[15]==active[0]:
                calls.append(active[1:]);changedcycles+=active[1];active=None
assert calls,'no complete C2P calls in the window'
inclusive=[c[0] for c in calls];main=[c[1] for c in calls]
print(f'completed C2P calls: {len(calls)}')
print(f'inclusive cycles/call: {statistics.mean(inclusive):.0f} (range {min(inclusive)}..{max(inclusive)})')
print(f'main-task cycles/call: {statistics.mean(main):.0f} (range {min(main)}..{max(main)})')
print(f'complete calls: {100*changedcycles/allcycles:.2f}% of all window cycles (boundary calls excluded)')
