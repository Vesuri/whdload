#!/usr/bin/env python3
"""Native p=5 helper twins from actual physics calls in a retained CPU trace.
Identity rates/reference values and original LSR #6 displacement must preserve
D1-A6. Units independently cover signed extremes and remainder arithmetic.
"""
import argparse,json,re,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from check_units import MARK

def check(p):
 m=json.loads((p/'capture.json').read_text());base=m['base'];slave=m['regions']['slave']
 ram=(p/'trace-start/code.bin').read_bytes()
 syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
 at=ram.index(MARK)+len(MARK);at=(at+1)&~1
 slave=base+at-syms['verify_unit_results']
 period=int.from_bytes(ram[slave+syms['sim_p']-base:slave+syms['sim_p']-base+2],'big');assert period==5
 names=['sim_scale_long','sim_distance','sim_traffic_delta','sim_reference_velocity','sim_coarse_rate']
 entries={slave+syms[n]:n for n in names};pending={};counts=collections.Counter();examples={};nonzero=collections.Counter()
 t=barto.load(str(p/'trace.bin'))
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc in entries:
    name=entries[pc];sp=r[15]
    assert sp not in pending,'reused active helper frame'
    pending[sp]=(name,r[:])
   if pc is None or pc==0x7fffffff or not base<=pc<base+len(ram):continue
   if ram[pc-base:pc-base+2]!=b'\x4e\x75' or r[15] not in pending:continue
   name,initial=pending.pop(r[15]);expected=initial[0]>>6 if name=='sim_distance' else initial[0]
   assert r[0]==expected,(name,f.index,initial[0],r[0],expected)
   assert r[1:15]==initial[1:15],(name,'clobbered preserved register')
   counts[name]+=1;nonzero[name]+=bool(initial[0]);examples.setdefault(name,dict(input=initial[0],output=r[0]))
 return dict(period=5,completed_calls=dict(counts),nonzero_inputs=dict(nonzero),examples=examples,scope='Actual moving-game rate/reference/traffic/coarse-rate identity and original displacement; intentional clock/clutch/RNG/geometry differences excluded')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('captures',nargs='+',type=Path);a=p.parse_args()
 reports={str(x):check(x) for x in a.captures};counts=collections.Counter();nonzero=collections.Counter()
 for r in reports.values():counts.update(r['completed_calls']);nonzero.update(r['nonzero_inputs'])
 required=['sim_scale_long','sim_distance','sim_traffic_delta','sim_reference_velocity','sim_coarse_rate']
 assert all(counts[n]>=5 for n in required),('unexercised helper across supplied windows',counts)
 assert all(nonzero[n]>0 for n in required),('only zero inputs exercised',nonzero)
 print(json.dumps(dict(status='PASS',captures=reports,completed_calls=dict(counts),nonzero_inputs=dict(nonzero)),indent=2))
