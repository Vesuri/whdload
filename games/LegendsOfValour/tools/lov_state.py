#!/usr/bin/env python3
"""Read the mapped frame clock, player heading and visible-object render records from a capture.
A4 is h11+$8000. Object pointer array/count come from h5:01f2a; types are numeric
because this tool does not identify the townsman or his world coordinates. Chip snapshots are
optional; unresolved pointers are reported instead of silently reading stale data.
"""
import argparse,json,os
from pathlib import Path
from lov_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--base',type=lambda x:int(x,0),default=0xc00000)
a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
b=(a.capture/'code.bin').read_bytes();chip=(a.capture/'chip.bin').read_bytes() if (a.capture/'chip.bin').exists() else b''
r={n:lo for lo,hi,n,o in regions(b,a.base,chip)}
def read(at,n):
    if a.base<=at and at+n<=a.base+len(b):return b[at-a.base:at-a.base+n]
    if at+n<=len(chip):return chip[at:at+n]
    return None
def number(at,n=2,signed=False):
    data=read(at,n)
    return int.from_bytes(data,'big',signed=signed) if data is not None else None
h11,h12=r['h11'],r['h12']
state=dict(gamefield=number(h11+0x602c,4),heading=number(h11+0x8c28),
           player_x=number(h11+0x8c1c,signed=True),player_y=number(h11+0x8c20,signed=True),
           movement_step=number(h12+0xcdd6),animation_frames=number(h11+0xdf6),objects=[])
count=number(h11+0x8c3c);assert count<=256,'implausible object count'
for i in range(count):
    ptr=number(h11+0x9fb4+4*i,4)
    if not ptr:continue
    state['objects'].append(dict(index=i,type=number(ptr+2,1),flags=number(ptr+3,1),
        x=number(ptr+10,signed=True),y=number(ptr+12,signed=True),z=number(ptr+14,signed=True)))
print(json.dumps(state,indent=2))
