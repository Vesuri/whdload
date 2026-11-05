#!/usr/bin/env python3
"""Independent integer model plus complete camera-cycle native regression."""
import json,struct
from pathlib import Path
from harness import ROOT
A=0x7ffe
u=lambda b,o:struct.unpack_from('>H',b,A+o)[0]
w=lambda b,o:struct.unpack_from('>h',b,A+o)[0]
l=lambda b,o:struct.unpack_from('>i',b,A+o)[0]
def trunc(n,d):return n//d if n>=0 else -((-n)//d)
def model(f,lane,fixed):
 scale=59636 if f==0 else 65535-(((-f&65535)*5899)>>16)
 partial=32767 if f==0 else max(1,(-f&65535)>>1)
 x=160*65536-lane*65535;y=160*65536;flag=0;pending=True
 for row in range(40):
  if fixed and pending and y>>16<125:
   x+=lane*65535-trunc(lane*scale*12288,5899);pending=False
  dy=scale*8
  if partial:dy=((dy>>8)*partial)>>7
  y-=dy
  if y>>16>=125:flag=1
  elif flag:flag=0
  else:
   prod=lane*scale;x+=(prod>>2)-(prod>>4)
  scale=scale*59637>>16;partial=0
 return x,y,scale
reports={}
for side,lane in [('left',-180),('center',0),('right',180)]:
 arms={}
 for arm,fixed in [('before',False),('after',True)]:
  folder=ROOT/'tmp/road-shift'/('flat-'+arm+'-'+side);frames=sorted(folder.glob('frame-*.bin'));assert len(frames)==66
  residual=[];scan={}
  for p in frames:
   b=p.read_bytes();f=u(b,-22338);expected=model(f,lane,fixed)
   assert w(b,-29832)==40
   actual=(l(b,-29844),l(b,-29848),u(b,-29852))
   assert actual==expected,(str(p),expected,actual)
   residual.append((actual[0]+trunc(lane*actual[2]*12288,5899))/65536)
   scan[f]=[w(b,-29208+y*2) for y in range(82,116)]
  assert len(scan)==64
  span=max(residual)-min(residual)
  if fixed:assert span<0.1,(side,span)
  elif lane:assert span>15,(side,span)
  arms[arm]=dict(frames=len(frames),phases=len(scan),projection_drift_pixels=span,scanlines=scan)
 if not lane:assert arms['before']['scanlines']==arms['after']['scanlines'],'center changed'
 for x in arms.values():del x['scanlines']
 reports[side]=arms
# Exhaust every phase with both signs: no tolerance based only on chosen captures.
for lane in [-1000,-180,-1,0,1,180,1000]:
 vals=[]
 for f in range(65536):
  x,y,s=model(f,lane,True);vals.append((x+trunc(lane*s*12288,5899))/65536)
 assert max(vals)-min(vals)<1.0,(lane,min(vals),max(vals))
print(json.dumps(dict(status='PASS',native=reports,exhaustive_phases=65536,signed_lanes=7,scope='Projection drift isolated from native scanline raster rounding; center scanlines unchanged'),indent=2))
