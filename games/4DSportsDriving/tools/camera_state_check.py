#!/usr/bin/env python3
"""Check camera-only changes, valid fractions, history/reset, and native fixture."""
import argparse,json,struct,re
from pathlib import Path
from simulation_fixture import read_fixture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('reference',type=Path);p.add_argument('--native',action='store_true');a=p.parse_args()
b=(a.capture/'memory.bin').read_bytes();old=(a.reference/'memory.bin').read_bytes()
m=json.loads((a.capture/'anchor.json').read_text());om=json.loads((a.reference/'anchor.json').read_text());assert m['simulation_tick']==om['simulation_tick']
for marker,want in [(b'4DHISTST',(6,40,40)),(b'4DSCHTST',(1,2,2)),(b'4DAUXTST',(1,1186,1186))]:
 o=b.index(marker);assert struct.unpack_from('>HHI',b,o+8)==want
q=b.index(b'4DCAM050');assert struct.unpack_from('>HH',b,q+8)==(1,8) and b[q+20:q+24]==b'CAMG'
def valid(state):
 assert len(state)==8 and all(v<5 for v in state[:2]+state[4:6]) and not any(state[2:4]+state[6:])
valid(b[q+12:q+20])
l=read_fixture(a.capture);r=read_fixture(a.reference);assert len(l)==len(r)
diffs=set()
for (tick,mode,now),(ot,oh,was) in zip(l,r):
 assert (tick,mode)==(ot,oh) and len(now)==1486 and len(was) in (1286,1478,1486)
 valid(now[1478:])
 d=[i for i,(x,y) in enumerate(zip(now,was)) if x!=y];diffs.update(d)
 if len(was)==1486 or mode!=50:assert not d, (tick,d)
 else:assert all(0x120<=i<0x138 for i in d),(tick,d)
 if mode!=50:assert not any(now[len(was):])
result=dict(samples=len(l),state_bytes=1486,changed_offsets=sorted(diffs),fractions_valid=True,history_checks=40,reset_checks=2)
if a.native:
 i=b.index(b'4DCAMNAT');v,n,done,case,phase,nonzero=struct.unpack_from('>HHIHHI',b,i+8)
 assert (v,n,done)==(1,1533,1533) and nonzero>0
 s={n:int(x,16) for n,x in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',(a.capture/'slave.lst').read_text(encoding='latin1'),re.M)}
 base=b.index(b'4DTAPE!!')+8-s['tape_game'];o=base+s['sim_camera_original']
 pristine=(Path('tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes())[0x28:]
 assert b[o:o+0x398]==pristine[0x7d56:0x80ee] and b[o+0x398:o+0x39c]==b'CMN2'
 result.update(native_cases=511,native_checks=done,nonzero_fraction_observations=nonzero,original_camera_bytes=0x398)
(a.capture/'camera-state-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
