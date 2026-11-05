#!/usr/bin/env python3
"""Observe actual cockpit camera updates at rendered-frame boundaries, read-only."""
import argparse,json,struct,tempfile
from pathlib import Path
from state_fields import command
from i500_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('frames',type=int);p.add_argument('out',type=Path)
p.add_argument('dump',type=Path);p.add_argument('base',type=lambda s:int(s,0));a=p.parse_args()
b=a.dump.read_bytes();r={n:(lo,hi) for lo,hi,n,o in regions(b,a.base)};g=r['game'][0]
lo,hi=r['slave'];m=b.find(b'I5MO',lo-a.base,hi-a.base);assert m>=0
stamp=a.base+m+12;a.out.mkdir(parents=True,exist_ok=True);rows=[]
with tempfile.TemporaryDirectory(prefix='i500-driving-') as temp:
 f=Path(temp)/'frame.bin';sf=Path(temp)/'stamp.bin';mf=Path(temp)/'mode.bin'
 for i in range(a.frames):
  command(f'''break *{g+0x276:#x}
continue
delete
dump binary memory {f} {g+0x7a8:#x} {g+0x7ba:#x}
dump binary memory {sf} {stamp:#x} {stamp+4:#x}
dump binary memory {mf} {g+0x268da:#x} {g+0x268db:#x}''')
  assert mf.read_bytes()==b'\x00','not a live driving session'
  rows.append(dict(frame=i,stamp=int.from_bytes(sf.read_bytes(),'big'),camera=list(struct.unpack('>9H',f.read_bytes()))))
pairs=list(zip(rows,rows[1:]));same=[(x,y) for x,y in pairs if x['stamp']==y['stamp']]
result=dict(frames=rows,camera_changes=sum(x['camera']!=y['camera'] for x,y in pairs),same_tick_pairs=len(same),same_tick_camera_changes=sum(x['camera']!=y['camera'] for x,y in same))
(a.out/'driving.json').write_text(json.dumps(result,indent=2)+'\n')
print(f"{len(rows)} cockpit frames: {result['camera_changes']} camera changes; {result['same_tick_camera_changes']}/{len(same)} same-tick pairs move")
