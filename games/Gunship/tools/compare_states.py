#!/usr/bin/env python3
"""Compare tick-boundary snapshots. Exit 0 only for equality.

Raw comparison is deliberately strict: clocks, RNG and renderer state are retained.
Use --expect-different as a negative control. Cross-CPU state equality belongs to C;
this reports differences instead of silently masking fields that have not been audited.
"""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('left',type=Path);p.add_argument('right',type=Path);p.add_argument('--expect-different',action='store_true');p.add_argument('--whole-ram',action='store_true',help='Also compare all fast RAM, including pointer-backed allocations');a=p.parse_args()
files=['h0.bin','h2.bin','h4.bin','h5.bin','h6.bin','mission.bin','alive.bin']
if a.whole_ram:files.append('fast.bin')
report={}
for name in files:
 x=(a.left/name).read_bytes();y=(a.right/name).read_bytes()
 offsets=[i for i in range(max(len(x),len(y))) if x[i:i+1]!=y[i:i+1]]
 report[name]=dict(equal=not offsets,different_bytes=len(offsets),first_offsets=[hex(i) for i in offsets[:20]])
# A useful semantic diagnostic, with no tick counter or incidental renderer pointers.
x=(a.left/'h6.bin').read_bytes();y=(a.right/'h6.bin').read_bytes()
report['player_without_tick']=dict(equal=x[0x3b88:0x3b94]+x[0x3b96:0x3be8]==y[0x3b88:0x3b94]+y[0x3b96:0x3be8])
print(json.dumps(report,indent=2))
equal=all(v['equal'] for v in report.values())
raise SystemExit(0 if equal != a.expect_different else 1)
