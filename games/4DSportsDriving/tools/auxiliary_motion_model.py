#!/usr/bin/env python3
"""Independent integer derivation for A2500 fragment motion at 50Hz.
No game hooks yet. Native16-bit velocity wrap is outside these reachable-range
cases; a runtime implementation must preserve its explicit storage semantics.
"""
import json
from pathlib import Path

def native(v,n):
 y=0
 for _ in range(n):
  v-=19;y+=v
 return v,y

def a4000(v,n):
 vf=0;yf=0;y=0
 for _ in range(n):
  # Keep the 20Hz kick-then-drift trajectory at common100ms boundaries.
  dy,yf=divmod(10*v+2*vf-133+yf,25)
  dv,vf=divmod(vf-38,5)
  v+=dv;y+=dy
 return v,y,vf,yf

vertical=0
for v in (-10000,-777,-19,-1,0,1,19,384,575,1000,10000):
 for blocks in (1,2,3,10,20,50,100):
  expected=native(v,2*blocks);actual=a4000(v,5*blocks)
  assert actual==(*expected,0,0),(v,blocks,expected,actual)
  vertical+=1
horizontal=0
for velocity in (-32768,-10000,-19,-1,0,1,19,384,10000,32767):
 for blocks in (1,2,10,100):
  x=r=0
  for _ in range(5*blocks):
   dx,r=divmod(2*velocity+r,5);x+=dx
  assert x==2*velocity*blocks and r==0
  horizontal+=1
angles=0
for initial in (0,1,0x3ff,0x7fff,0xffff):
 a=initial;r=0
 for step in range(1,501):
  da,r=divmod(32+r,5);a=(a+da)&65535
  if step%5==0:
   assert a==(initial+32*(step//5))&65535 and r==0
   angles+=1
result=dict(vertical_common_boundary_cases=vertical,horizontal_cases=horizontal,angle_common_boundaries=angles,reference='A2500 20Hz',new_rate=50,claim='integer model only; native hook, retirement and replay integration remain unimplemented')
p=Path(__file__).resolve().parents[1]/'tmp/analysis/auxiliary-motion-model.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
