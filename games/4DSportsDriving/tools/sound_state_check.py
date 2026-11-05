#!/usr/bin/env python3
"""Require unchanged native/RNG/private/time samples after sound-only changes."""
import argparse, json, struct
from pathlib import Path
from simulation_fixture import read_fixture
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path);p.add_argument('reference',type=Path)
a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();old=(a.reference/'memory.bin').read_bytes()
m=json.loads((a.capture/'anchor.json').read_text());om=json.loads((a.reference/'anchor.json').read_text())
assert m['simulation_tick']==om['simulation_tick']
i=b.index(b'4DAUDTST');assert struct.unpack_from('>HHI',b,i+8)==(1,42,42)
i=b.index(b'4DAUD050');assert struct.unpack_from('>HH',b,i+8)==(1,12) and b[i+24:i+28]==b'AUDG'
assert struct.unpack_from('>H',b,i+12)[0]<=40 and struct.unpack_from('>H',b,i+14)[0]==0
l=read_fixture(a.capture);r=read_fixture(a.reference)
assert len(l)==len(r) and len(l)>=9
for (tick,mode,now),(ot,oh,was) in zip(l,r):
 assert (tick,mode)==(ot,oh)
 assert len(was) in (1286,1478,1486) and len(now) in (1478,1486)
 assert now[:len(was)]==was, ('sample',tick)
 assert not any(now[len(was):]), ('new auxiliary bytes',tick)
def native(blob,meta):
 aa=meta['data_base']+0x7ffe-meta['memory_base']
 ph=blob.index(b'4DA4PHYS')+12;tm=blob.index(b'4DTSTATE')+12
 return blob[aa-0xa80:aa-0x620]+blob[aa+0x228:aa+0x22e]+blob[ph:ph+128]+blob[tm:tm+32]
assert native(b,m)==native(old,om), 'final native/RNG/car/time state'
r=dict(equal_samples=len(l),sample_bytes=len(l[0][2]),reference_bytes=len(read_fixture(a.reference)[0][2]),final_state_bytes=1286,selftests=42,sound_guard=True,tick=m['simulation_tick'],rate=l[0][1])
(a.capture/'sound-state-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
