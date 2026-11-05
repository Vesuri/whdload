#!/usr/bin/env python3
"""Check real startup preferences, menu state and memory guards."""
import argparse,json,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--loaded',type=int,required=True);p.add_argument('--saved',type=int,required=True);a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();i=b.index(b'4DPREFS!')
assert struct.unpack_from('>HH',b,i+8)==(1,16)
status,loads,saves,loaded=struct.unpack_from('>IIIH',b,i+12)
assert (status,loads,saves,loaded)==(1,1,a.saved,a.loaded),(status,loads,saves,loaded)
assert b[i+26:i+30]==b'PREF' and b[i+48:i+52]==b'END!'
j=b.index(b'4DMODEUI');opens,changes,old,new,active,recorded=struct.unpack_from('>II4H',b,j+12)
assert opens>=1 and changes==a.saved
if a.saved: assert (old,new,active,recorded)==(20,50,20,20)
else: assert (old,new,active,recorded)==(0,0,0,0)
m=json.loads((a.capture/'anchor.json').read_text());at=m['data_base']+0x7ffe-m['memory_base'];rate=50 if a.saved else a.loaded
assert struct.unpack_from('>H',b,at-0xbc)[0]==rate
assert struct.unpack_from('>H',b,at-0x15fa)[0]==rate and b[at-0x173a]==rate
r=dict(status=status,loads=loads,saves=saves,loaded=loaded,active_rate=rate,guards=True,menu_changes=changes)
(a.capture/'preferences-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
