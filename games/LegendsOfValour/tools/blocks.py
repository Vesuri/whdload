#!/usr/bin/env python3
"""Top 64-byte instruction blocks in a retained fixed-window capture."""
import argparse, bisect, collections, os
from pathlib import Path
import barto
from lov_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--base',type=lambda x:int(x,0),default=0xc00000)
a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
t=barto.load(str(a.capture/'trace.bin'))
r=sorted((lo,hi,n) for lo,hi,n,o in regions((a.capture/'code.bin').read_bytes(),a.base,t.chip))
starts=[lo for lo,hi,n in r];counts=collections.Counter();total=0
for field in t.fields:
    for pc,cost,regs in t.instructions(field):
        total+=cost
        if pc is None:continue
        i=bisect.bisect_right(starts,pc)-1
        if i>=0:
            lo,hi,name=r[i]
            if pc<hi:counts[name,(pc-lo)&~63]+=cost
for (name,offset),cost in counts.most_common(30):print(f'{100*cost/total:5.2f}  {name}:{offset:05x}')
