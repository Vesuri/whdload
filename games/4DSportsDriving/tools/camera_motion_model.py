#!/usr/bin/env python3
"""Candidate camera scaling checks using the shipped Q14 trigonometric table."""
from pathlib import Path
import json,struct
root=Path(__file__).resolve().parents[1]
b=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
table=struct.unpack_from('>257h',b,0x3a1dc+0x7ffe-0x376a)
assert table[0]==0 and table[256]==16384 and all(a<=c for a,c in zip(table,table[1:]))
def sine(angle):
 a=angle&1023
 if a<=256:return table[a]
 if a<=512:return table[512-a]
 if a<=768:return -table[a-512]
 return -table[1024-a]
def native_mul(v,q):
 product=(v*q)&0xffffffff
 swapped=((product<<16)|(product>>16))&0xffffffff
 rotated=((swapped<<2)|(swapped>>30))&0xffffffff
 w=rotated&65535
 return w if w<32768 else w-65536
naive_errors=[];checks=0
for angle in range(1024):
 for q in (sine(angle),sine(angle+256)):
  nominal=native_mul(120,q)
  assert nominal==(120*q)//16384
  naive_errors.append(5*native_mul(48,q)-2*nominal)
  x=carry=0
  for _ in range(5):
   step,carry=divmod(2*nominal+carry,5);x+=step
  assert x==2*nominal and carry==0
  checks+=1
clamp=lambda x,n:max(-n,min(n,x))
for error in range(-32768,32768):
 a=c=error
 for _ in range(2):a-=clamp(a,30)
 for _ in range(5):c-=clamp(c,12)
 assert a==c
for error in range(32768):
 a=c=error
 for _ in range(2):a-=min(a,120)
 for _ in range(5):c-=min(c,48)
 assert a==c
r=dict(status='analysis model, no camera runtime patch',fixed_heading_component_checks=checks,naive_cap_only_different_components=sum(e!=0 for e in naive_errors),naive_cap_only_error_range=[min(naive_errors),max(naive_errors)],vertical_fixed_target_checks=65536,axial_horizontal_fixed_target_checks=32768,current_50hz_horizontal_units_per_second=50*240,a2500_horizontal_units_per_second=20*120,current_50hz_vertical_units_per_second=50*30,a2500_vertical_units_per_second=20*30,candidate_vertical_cap=12,candidate_horizontal_threshold=48)
p=root/'tmp/analysis/camera-motion-model.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
