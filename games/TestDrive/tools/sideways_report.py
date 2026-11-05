#!/usr/bin/env python3
"""Validate all mountain layers against the native atomic latch and quantify steps."""
import argparse,json,re
from pathlib import Path

def wrap_deg(x):return (x+180*65536)%(360*65536)-180*65536
def wrap_pixel(x):
 while x < -400:x+=800
 while x > 400:x-=800
 return x

def report(folder):
 meta=json.loads((folder/'metadata.json').read_text());enhanced=not meta['options']['C1']&16
 count=corrected=frac_lane=0;steps=[];raw_steps=[];previous=None;layers=[]
 for line in (folder/'gdb.txt').read_text().splitlines():
  match=re.search(r'(LATCH|DRAW) .+',line)
  if not match:continue
  line=match[0]
  if line.startswith('LATCH '):
   vals=list(map(int,line.split()[1:]));vbl,pos,lat,raw,ref,oldseg,prev,last,*phase=vals
   seg=pos>>16;f=(pos&65535)>>1
   if oldseg!=seg:
    prev=raw if oldseg==-1 or seg<oldseg else last
   else:prev+=raw-last
   diff=wrap_deg(raw-prev)>>8
   smooth=raw if not -32768<=diff<=32767 else prev+((diff*f)>>7)
   delta=wrap_deg(smooth-ref*65536)
   expected=[wrap_pixel((x-delta*(5 if i<2 else 6))>>16) for i,x in enumerate(phase)]
   native=[x>>16 for x in phase]
   frac_lane+=bool(lat&65535);corrected+=expected!=native;count+=1;layers=[]
  elif line.startswith('DRAW '):
   layer,x,y=map(int,line.split()[1:]);x=(x+32768)%65536-32768
   assert layer==len(layers),(line,layers)
   if enhanced:assert x==expected[layer],(count,layer,x,expected[layer],vals)
   layers.append(x)
   if layer==3:
    if previous is not None:
     steps.append(abs(wrap_pixel(x-previous[0])));raw_steps.append(abs(wrap_pixel(native[3]-previous[1])))
    previous=(x,native[3])
 assert count==meta['frames'] and len(layers)==4,(count,meta)
 if enhanced:assert corrected>0,'capture must exercise fractional heading, not just a flat stationary frame'
 return dict(status='PASS',frames=count,layer_outputs=count*4,fractionally_corrected_frames=corrected,fractional_lane_frames=frac_lane,max_draw_step=max(steps,default=0),max_integer_reference_step=max(raw_steps,default=0),draw_steps=steps,integer_steps=raw_steps)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);a=p.parse_args();print(json.dumps(report(a.capture),indent=2))
