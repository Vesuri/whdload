#!/usr/bin/env python3
"""Independent fixed-width model for TD's streamed road and fractional traffic."""
import argparse,json,struct,hashlib
from pathlib import Path
from harness import ROOT
from audit_simulation import originals
ROOT_CODE=originals()["root"]
A=0x7ffe
s16=lambda x:(x+32768)%65536-32768
s32=lambda x:(x+2**31)%2**32-2**31
w=lambda b,o:struct.unpack_from('>h',b,A+o)[0]
u=lambda b,o:struct.unpack_from('>H',b,A+o)[0]
l=lambda b,o:struct.unpack_from('>i',b,A+o)[0]
def sine(x):
 b=ROOT_CODE;i=x>>16
 assert 0<=i<=90,(i,x)
 lo,hi=struct.unpack_from('>HH',b,0x216c+2*i)
 return lo+((hi-lo)*(x&65535)>>16)
def fixed(x,scale):return s32((x*scale)//65536)
def trunc(n,d):return (-1 if n<0 else 1)*(abs(n)//d)
def validate(folder,enhanced=True,zero=False,lane_seed=False):
 parent=folder
 while not (parent/'capture.json').exists():
  if parent==parent.parent:raise FileNotFoundError('capture.json')
  parent=parent.parent
 meta=json.loads((parent/'capture.json').read_text());ram=(parent/'code.bin').read_bytes();chip=(parent/'chip.bin').read_bytes()
 def read(addr,n):
  return ram[addr-meta['base']:addr-meta['base']+n] if meta['base']<=addr<meta['base']+len(ram) else chip[addr:addr+n]
 def descriptor(b,segment):
  idx=read(l(b,-26232)+segment,1)[0]
  assert idx!=255
  return read(l(b,-26228)+idx*4,4)
 result={};fine=enhanced and not zero
 for view in ['main','mirror']:
  paths=sorted(folder.glob(view+'-[0-9][0-9].bin'));assert len(paths)>6
  first=paths[0].read_bytes();f=u(first,-22338)>>1
  slope=0;rows=[];errors=[];lane_pending=bool(lane_seed and fine and view=="main")
  if view=='mirror' and fine and f:
   seed=descriptor(first,w(first,-22340)+1)
   slope=0  # the prefixed row has the original row-zero clamp
   assert l(first,-29840)==struct.unpack('b',seed[1:2])[0]*f>>2
   assert u(first,-29852)==20480+(-1844*f>>15)
   assert l(first,-29848)==62*65536-5*f
   x=l(first,-22372)
   prefix=((fixed(x,20480)>>3)>>8)*f>>7
   assert l(first,-29844)==280*65536-(x*5>>4)+prefix
  elif view=='mirror':
   assert u(first,-29852)==20480 and l(first,-29848)==62*65536
   x=l(first,-22372)
   expected=280*65536-(x*5>>4) if fine else (280-(s16(x>>16)*5>>4))*65536
   assert l(first,-29844)==expected
  else:
   scale=59636 if fine and not u(first,-22338) else 65535-((((-u(first,-22338))&65535)*5899)>>16)
   assert u(first,-29852)==scale
   x=l(first,-22372) if fine else w(first,-22372)<<16
   assert l(first,-29844)==160*65536-fixed(x,65535 if fine else scale)
  for idx,path in enumerate(paths):
   b=path.read_bytes();desc=path.with_name(path.stem+'-desc.bin').read_bytes()
   mirror=bool(w(b,-28800));scale=u(b,-29852);partial=u(b,-29308)
   x,y,curve=l(b,-29844),l(b,-29848),l(b,-29840)
   # Captures stop before render_row: apply its seed before drawing/updating.
   if lane_pending and y>>16<125:
    lane=l(b,-22372)
    x=s32(x+fixed(lane,65535)-trunc(fixed(lane,scale)*12288,5899))
    lane_pending=False
   sw=w(b,-29836)
   if s16(slope>>16)!=sw:slope=sw<<16
   rows.append([x>>16,y>>16,scale,w(b,-29834)])
   # Original first span is already camera-fraction weighted.
   dy=scale*8
   if partial:dy=((dy>>8)*partial)>>7
   sp=-sw if mirror else sw
   extra=(((slope&65535)*scale)>>16)>>2 if fine else 0
   y=s32(y-dy-((sp*scale)>>2)+(extra if mirror else -extra))
   flag=w(b,-26210)
   if not mirror and (y>>16>=125 or flag):curve=l(b,-26186)
   else:
    sv=sine(abs(curve));prod=s16((sv*(40 if mirror else 80))>>8)*scale
    shift=s32(prod)>>8
    x=s32(x-shift if curve<0 else x+shift)
    p=w(b,-22372)*scale
    frac=(u(b,-22370)*scale)>>16 if fine else 0
    if mirror:x=s32(x-((-p)>>3)+(frac>>3))
    else:
     p>>=2;frac>>=2;x=s32(x+p-(p>>2)+frac-(frac>>2))
   dc=struct.unpack('b',desc[1:2])[0]
   curve=s32(curve+((dc*partial*2 if partial else dc<<16)>>3))
   high=s16(curve>>16);high=max(-90,min(90,high));curve=s32((high<<16)|(curve&65535))
   coeff=scale
   if partial:coeff=(coeff*partial*2)>>16
   if mirror:coeff*=2
   coeff=s16((0x48000-coeff*4)>>4)
   ds=struct.unpack('b',desc[2:3])[0]*coeff
   slope=s32(slope+ds) if fine else s16(sw+(ds>>16))<<16
   limit=struct.unpack_from('b',b,A-29894+idx)[0]
   if fine:
    bound=limit<<16
    if mirror or idx:bound+=(struct.unpack_from('b',b,A-29894+idx+(1 if mirror else -1))[0]-limit)*u(b,-22338)
    slope=max(-bound,min(bound,slope));clamped=s16(slope>>16)
   else:
    clamped=max(-limit,min(limit,s16(slope>>16)))
    if clamped!=s16(slope>>16):slope=clamped<<16
   next_scale=(scale*59637)>>16
   expected=dict(x=x,y=y,curve=curve,slope=clamped,scale=next_scale)
   if idx+1<len(paths):
    nxt=paths[idx+1].read_bytes();actual=dict(x=l(nxt,-29844),y=l(nxt,-29848),curve=l(nxt,-29840),slope=w(nxt,-29836),scale=u(nxt,-29852))
    if expected!=actual:errors.append(dict(row=idx,expected=expected,actual=actual,base_changed=l(nxt,-26186)!=l(b,-26186)))
  # Independently reconstruct post-walker queue changes, including near-plane
  # and last-row exclusions, unsigned scale and signed division toward zero.
  before=(folder/(view+'-before.bin')).read_bytes();after=(folder/(view+'-after.bin')).read_bytes()
  count=u(before,-28798);car_count=0;car_changes=0
  for i in range(count):
   typ=w(before,-27996+2*i);pos=None
   if 16<=typ<=20:pos=-29350+4*(typ-16)
   if 25<=typ<=29:pos=-29374+4*(typ-24)
   original=[w(before,-28796+2*i),w(before,-28396+2*i),u(before,-27596+2*i)]
   expected=original[:]
   if pos is not None:
    car_count+=1;segment=w(before,pos);camera=w(before,-22340);row=camera-segment if view=='mirror' else segment-camera
    f=u(before,pos+2)>>1
    if enhanced and f and 6<row<len(rows) and (view=='mirror' or row+1<len(rows)):
     a=rows[row];z=rows[row-1 if view=='mirror' else row+1]
     ds=(z[2]-a[2])*f>>15
     expected[2]=s16(expected[2]+ds)&65535
     expected[0]=s16(expected[0]+trunc((original[0]-a[0])*ds,a[2])+((z[0]-a[0])*f>>15))
     expected[1]=s16(expected[1]+((min(z[1],z[3])-min(a[1],a[3]))*f>>15))
   actual=[w(after,-28796+2*i),w(after,-28396+2*i),u(after,-27596+2*i)]
   assert expected==actual,(view,i,typ,expected,actual)
   car_changes+=original!=actual
  result[view]=dict(rows=len(rows),road_errors=errors,cars=car_count,changed_cars=car_changes)
 assert not any(x['road_errors'] for x in result.values()),result
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--original',action='store_true');p.add_argument('--zero',action='store_true');p.add_argument('--lane-seed',action='store_true');a=p.parse_args();print(json.dumps(validate(a.capture,not a.original,a.zero,a.lane_seed),indent=2))
