#!/usr/bin/env python3
"""Compare paired ordinary-input stall captures without masking state bytes."""
import json,re,struct,hashlib,sys
from pathlib import Path
caps=list(map(Path,sys.argv[1:]))
assert len(caps)==2
def state(cap,name):
 m=json.loads((cap/'anchor.json').read_text());b=(cap/name).read_bytes()
 sy={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
 base=m['marker']+8-sy['tape_game']-m['memory_base']
 aa=m['data_base']+0x7ffe-m['memory_base']
 result=b[aa-0xa80:aa-0x620]+b[aa+0x228:aa+0x22e]
 for symbol,size in [('sim_a4000_private',152),('sim_results_state',32),('sim_aux_state',192),('sim_camera_state',8)]:
  at=base+sy[symbol];result+=b[at:at+size]
 assert len(result)==1510
 return result
checks=[]
for name in ('memory.bin','state-150.bin','state-200.bin','state-250.bin','state-300.bin'):
 left,right=[state(c,name) for c in caps]
 diff=[i for i,(a,b) in enumerate(zip(left,right)) if a!=b]
 checks.append(dict(snapshot=name,equal=not diff,differences=diff,sha256=[hashlib.sha256(v).hexdigest() for v in (left,right)]))
result=dict(state_checks=checks,scope='Unmasked1510-byte native/RNG/private/time/auxiliary/camera state at matching checkpoints. Input and stall timing require separate window checks.')
out=caps[0].parent/'paired-state.json';out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert all(c['equal'] for c in checks)
