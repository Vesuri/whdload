#!/usr/bin/env python3
"""Count sideways steps in sideways_fields.py captures: for the mountains (backdrop d2),
the drawn and raw heading and the drawn and raw lane, print nonzero frame-to-frame steps,
their largest size and how often consecutive steps reverse direction (jitter).
  sideways_report.py OUT/sideways [OUT2/sideways ...] [--until FIELD]
Compare steering captures over the same field prefix (--until). Do not judge
smoothness by road-row index: a row is a moving world point reassigned each segment.
"""
import argparse
from pathlib import Path

def records(capture):
    bd=[];rw=[]
    for line in (Path(capture)/'gdb.txt').read_text().splitlines():
        p=line.split()
        if p[:1]==['BD']:bd.append([int(x) for x in p[1:]])
        if p[:1]==['RW']:rw.append([int(x) for x in p[1:]])
    return bd,rw

def steps(values):
    d=[b-a for a,b in zip(values,values[1:]) if b!=a]
    reversals=sum(1 for a,b in zip(d,d[1:]) if (a>0)!=(b>0))
    return len(d),max((abs(x) for x in d),default=0),reversals

p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('captures',nargs='+');p.add_argument('--until',type=int)
a=p.parse_args()
for capture in a.captures:
    bd,rw=records(capture)
    if a.until is not None:
        bd=[r for r in bd if r[5]<=a.until];rw=[r for r in rw if r[1]<=a.until]
    print(f'{capture}: {len(bd)} backdrop computations, {len(rw)} main views')
    series=[('mountains d2 (px)',[r[0] for r in bd]),
            ('drawn heading/4',[r[2] for r in rw]),('raw heading',[r[4] for r in rw])]
    if rw and len(rw[0])>6:  # lane longs; early captures recorded only the drawn integer
        series+=[('drawn lane (units)',[r[5]/65536 for r in rw]),('raw lane (units)',[r[6]/65536 for r in rw])]
    for name,values in series:
        n,biggest,reversals=steps(values)
        print(f'  {name:19s} {n:4d} steps, largest {biggest:g}, {reversals} reversals')
