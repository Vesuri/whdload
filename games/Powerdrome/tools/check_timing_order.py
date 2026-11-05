#!/usr/bin/env python3
"""Compare every sampled logical control speed across matched timed input routes."""
import argparse
import json
from pathlib import Path
from coverage_status import fixture
from timing_report import NAMES

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
p.add_argument('--accounted-endpoints',action='store_true',help='Derive endpoint counts from WORLD20 and physical clock accounting')
a=p.parse_args()
assert len(a.captures)>=2, 'Need at least two CPU/render configurations'
runs=[]
for root in a.captures:
    config=json.loads((root/'configuration.json').read_text())
    assert 'CUSTOM5=9' in config['WHD_ARGS']
    epoch=fixture(root/'code.bin')['epoch']*4
    rows=[]; sample=None
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        parts=line.split()
        if len(parts)<3 or parts[2]!='0xd058': continue
        if parts[0]=='PDTIME_EVENT':
            sample=dict(zip(NAMES,[int(parts[1])]+list(map(int,parts[3:]))))
        elif parts[0]=='PDINPUT_EVENT':
            assert sample is not None and int(parts[1])==sample['field']
            tick,consumed,mode,active,joy,x,y=map(int,parts[3:])
            rows.append((tick-epoch,sample['speed'],consumed,joy,x,y))
            sample=None
    assert len(rows)>=50 and all(b[0]-a[0]==18 for a,b in zip(rows,rows[1:])), 'Missing logical samples'
    if a.accounted_endpoints:
        from timing_control_window import check_control_window
        check_control_window(root,[row[0] for row in rows],epoch)
    runs.append(rows)
# Capture endpoints can interrupt a frame; compare the complete common logical window.
if a.accounted_endpoints:
    assert len({int(json.loads((root/'configuration.json').read_text())['FIELDS']) for root in a.captures})==1, 'Physical capture durations differ'
length=min(map(len,runs))
if not a.accounted_endpoints:
    assert max(map(len,runs))-length<=1, 'More than one endpoint update differs'
reference=runs[0][:length]
assert reference[-1][2]==6, 'Common window does not include release'
for root,rows in zip(a.captures[1:],runs[1:]):
    for expected,actual in zip(reference,rows[:length]):
        assert expected==actual,(root.name,'first unequal logical speed/input state',expected,actual)
print(f'{len(reference)} complete common logical speed/input updates match across {len(runs)} captures, including braking and release')
