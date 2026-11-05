#!/usr/bin/env python3
"""Check private-profiler boot against the same slave on the original emulator."""
import argparse,json,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('reference',type=Path);a=p.parse_args()
def read(cap):
 m=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();aa=m['data_base']+0x7ffe-m['memory_base']
 state=b[aa-0xa80:aa-0x620]+b[aa+0x228:aa+0x22e]
 for marker,size in [(b'4DA4PHYS',128),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  o=b.index(marker)+12;state+=b[o:o+size]
 ptr=struct.unpack_from('>I',b,aa-0x1770)[0]-m['memory_base']
 return m,state,b[ptr:ptr+m['simulation_tick']]
m,state,inputs=read(a.capture);old,reference,oldinputs=read(a.reference)
assert m['slave_sha256']==old['slave_sha256']
assert m['simulation_tick']==old['simulation_tick']
for k,v in old['settings'].items():assert m['settings'][k]==v,(k,v,m['settings'][k])
assert len(state)==len(reference)==1486
r=dict(slave_sha256=m['slave_sha256'],tick=m['simulation_tick'],state_bytes=len(state),state_differences=[i for i,(x,y) in enumerate(zip(state,reference)) if x!=y],input_differences=[i for i,(x,y) in enumerate(zip(inputs,oldinputs)) if x!=y],input_bytes=len(inputs),reference=str(a.reference),scope='Unprofiled ordinary-input anchor only; does not by itself prove timing equivalence during active profiling.')
(a.capture/'profiler-equivalence.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert not r['state_differences'] and not r['input_differences']
