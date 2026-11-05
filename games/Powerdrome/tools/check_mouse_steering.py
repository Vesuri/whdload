#!/usr/bin/env python3
"""Check fine mouse captures and compare complete per-step states across render rates."""
import argparse
import re
from pathlib import Path
from timing_report import input_state

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',nargs='+',type=Path)
a=p.parse_args()
histories=[]
for root in a.captures:
    log=(root/'swaps-gdb.txt').read_text()
    rows=[list(map(int,s.split())) for s in re.findall(r'^PDMOUSE_EVENT \d+ 0xccee (.+)$',log,re.M)]
    assert len(rows)>=450, 'Need the whole horizontal and vertical single-count tape'
    assert all(len(r)==87 for r in rows), {len(r) for r in rows}
    assert all(r[0]==1 and r[1]==0 and r[72]==0 for r in rows),'Wrong fine-steering scope or input mode'
    # Single-count steering must produce fractional rates in both directions.
    # Independent braking jitter can also add whole-degree pitch during the tape.
    def long(r,off):
        i=(off-8)//2
        n=(r[i]<<16)|r[i+1]
        return n-(1<<32) if n&(1<<31) else n
    pitch={long(r,22) for r in rows}
    yaw={long(r,26) for r in rows}
    assert min(pitch)<0<max(pitch) and min(yaw)<0<max(yaw),(pitch,yaw)
    moving=[(x,y) for x,y in zip(rows,rows[1:]) if long(y,22) or long(y,26)]
    fine=[(x,y) for x,y in moving if y[2]>4 and x[-9:]!=y[-9:]]
    assert len(fine)>=25,'No demonstrated sub-control-epoch rotation'
    state=input_state(root/'final-code.bin')
    assert state['overflow']==0
    # Snapshot values, including the private Q28 matrices/remainders, must match.
    histories.append(rows)
    print(f'{root.name}: {len(rows)} world steps, {len(fine)} between-control matrix changes; pitch {sorted(pitch)}, yaw {sorted(yaw)} in Q12; no input overflow')
if len(histories)>1:
    n=min(map(len,histories))
    for root,rows in zip(a.captures[1:],histories[1:]):
        mismatch=next(((i,x,y) for i,(x,y) in enumerate(zip(histories[0][:n],rows[:n])) if x!=y),None)
        assert mismatch is None,(root.name,mismatch)
    print(f'All {n} common complete mouse/matrix states match exactly')
