#!/usr/bin/env python3
"""Audit saved combined-twin state at the requested driving anchor."""
import argparse,json,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--snapshot',default='memory.bin');a=p.parse_args();cap=a.capture
meta=json.loads((cap/'anchor.json').read_text());ram=(cap/a.snapshot).read_bytes();values={}
for tag,fmt in [(b'4DPERF!!','>IHHII'),(b'4DTWIN!!','>II'),(b'4DMTWIN!','>II'),(b'4DBOOK!!','>III'),(b'4DMATH!!','>I')]:
 at=ram.index(tag);values[tag.decode()]=struct.unpack_from(fmt,ram,at+8)
assert values['4DPERF!!'][0]==meta['game_base']
assert values['4DPERF!!'][1:4]==(0,0,0),'Guard left active or VERIFY failed'
assert values['4DPERF!!'][4]>0,'No guarded blitter work'
assert values['4DBOOK!!'][2]==57 and values['4DMATH!!'][0]==176
assert all(n>7 for n in values['4DTWIN!!']) and all(n>100 for n in values['4DMTWIN!'])
assert values['4DBOOK!!'][1]>48,'No live epilogue pairs'
at=meta['game_base']-meta['memory_base'];original=Path('tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
if meta['settings']['CPU']=='68EC020':
 assert ram[at+0xfc6:at+0xfcc]==original[0x28+0xfc6:0x28+0xfcc]
 assert values['4DBOOK!!'][0]==9,'Live clear must stay native on 68020'
else:
 assert ram[at+0xfc6:at+0xfcc]!=original[0x28+0xfc6:0x28+0xfcc]
 assert values['4DBOOK!!'][0]>9,'No live clear pairs'
(cap/(Path(a.snapshot).stem+'-verify-counters.json')).write_text(json.dumps(values,indent=2)+'\n')
frame=struct.unpack_from('>I',ram,ram.index(b'4DTAPE!!')+16)[0]
state=meta['data_base']-meta['memory_base']+0x7ffe
assert struct.unpack_from('>H',ram,state-0x15fa)[0]==10
assert ram[state-0x173a]==10
print(f"{cap.name}: snapshot {a.snapshot}, frame {frame}, detail {meta['graphics_level']}, active Normal, combined twins and CPU gate pass")
