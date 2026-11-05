#!/usr/bin/env python3
"""Native A4000 Save Replay filename-collision preservation check."""
from pathlib import Path
import json,struct,hashlib
r=Path('tmp/runtime-file-rejection');m=json.loads((r/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base']
def sem(b):
 v=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
 for marker,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=b.index(marker)+12;assert struct.unpack_from('>H',b,p-2)[0]==n;v+=b[p:p+n]
 assert len(v)==1510;return v
def ptr(b,o):return struct.unpack_from('>I',b,a+o)[0]-m['memory_base']
b=(r/'before-submit.bin').read_bytes();x=sem(b);samples=[]
for name in ('rejected','returned'):
 c=(r/(name+'.bin')).read_bytes();diff=[i for i,(q,w) in enumerate(zip(x,sem(c))) if q!=w];assert not diff,(name,diff)
 p=c.index(b'4DRPLSAV');assert struct.unpack_from('>HHII',c,p+8)==(1,0,0,0xffffffff)
 for off,n in [(-0x1770,30000),(-0x16bc,22400)]:
  p,q=ptr(b,off),ptr(c,off);assert b[p:p+n]==c[q:q+n],(name,off)
 p=b.index(b'4DHISTRY')+28;q=c.index(b'4DHISTRY')+28;assert b[p:p+7840]==c[q:q+7840]
 state=json.loads((r/(name+'.json')).read_text());assert state['consumer']==state['imported']==state['recorded_length']==340
 assert state['sim_schedule_ticks']==342 and state['perf_failure']==state['sim_schedule_overflow']==0
 samples.append(name)
h=hashlib.sha256(Path('tmp/run/default/.run/dh1/data/a4test.rpl').read_bytes()).hexdigest();launch=json.loads((r/'launch.json').read_text());assert h==launch['seed_sha256']
report=dict(runtime_sha256=launch['slave_sha256'],samples=samples,semantic_bytes_equal=1510,input_bytes_equal=30000,native_checkpoint_bytes_equal=22400,companion_bytes_equal=7840,save_dispatch_attempts=0,existing_file_sha256=h,recorded_end=340,guest_memory_modified=False,scope='Native A4000 moving-car recording, Save Replay filename editor, existing ABI9 filename rejection, acknowledgment/cancel and return to paused replay. Existing disk file and live replay buffers preserved. No overwrite or new-file persistence claim.')
(r/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
