#!/usr/bin/env python3
"""Compare jump traces, sampled complete states, and the complete final semantic state."""
import sys,json,re,hashlib
from pathlib import Path
from simulation_fixture import read_fixture,compare

def read(path):
 p=Path(path);m=json.loads((p/'anchor.json').read_text());d=json.loads((p/'bridge.json').read_text());mem=(p/'bridge-end.bin').read_bytes();a4=m['data_base']+0x7ffe-m['memory_base']
 syms={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['marker']+8-syms['tape_game']-m['memory_base']
 state=mem[a4-0xa80:a4-0xa80+0x460]+mem[a4+0x228:a4+0x22e]
 for symbol,size in [('sim_a4000_private',152),('sim_results_state',32),('sim_aux_state',192),('sim_camera_state',8)]:
  at=base+syms[symbol];state+=mem[at:at+size]
 assert len(state)==1510
 return d,read_fixture(p,'bridge-end.bin'),state
left,right=map(Path,sys.argv[1:3]);a,af,ab=read(left);b,bf,bb=read(right)
assert a['rate']==b['rate']==50 and a['first']==b['first'] and a['end']==b['end']
fixtures=compare(af,bf);changed=[i for i,(x,y) in enumerate(zip(ab,bb)) if x!=y]
result=dict(trace_records=len(a['rows']),identical_body_records=a['rows']==b['rows'],fixture_comparison=fixtures,final_semantic_bytes=len(ab),final_changed_offsets=changed,final_sha256=hashlib.sha256(ab).hexdigest(),passed=a['rows']==b['rows'] and fixtures['equal_samples']==fixtures['samples'] and not changed)
(right/'bridge-determinism.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
