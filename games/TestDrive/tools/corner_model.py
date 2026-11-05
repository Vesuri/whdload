"""Read-only native arithmetic model for main-view corner/near-plane continuity."""
import struct,sys,json
from pathlib import Path
from subunit_geometry import sine,s16,s32,trunc,l,u
from amigaxdev import barto
ROOT=Path(__file__).resolve().parents[1]; ref=ROOT/'tmp/corner-jump/curve-before'; b=(ref/'frame-00.bin').read_bytes();chip=barto.load(ref/'screen.bin').chip
t,d=l(b,-26232),l(b,-26228)
def model(segment,f,lane=0,bank=0,fix=True,heights=False,data=None):
 scale=59636 if f==0 else 65535-(((-f&65535)*5899)>>16)
 partial=32767 if f==0 else max(1,(-f&65535)>>1)
 x=160*65536-lane*65535;y=160*65536;flag=0;pending=True;curve=0;rows=[];slope=0
 limits=(data if data is not None else b)[0x7ffe-29894:0x7ffe-29894+40]
 for row in range(40):
  desc=chip[d+chip[t+segment+row]*4:d+chip[t+segment+row]*4+4]
  dc=s16(desc[1]<<8)>>8
  if pending and y>>16<125:
   x+=lane*65535-trunc(lane*scale*12288,5899);pending=False
  rows.append((x,y,scale,curve))
  py=y;dy=scale*8
  if partial:dy=((dy>>8)*partial)>>7
  y-=dy
  if heights:y-=((slope>>16)*scale>>2)+(((slope&65535)*scale>>16)>>2)
  if y>>16>=125:flag=1;curve=bank
  elif flag:
   flag=0;curve=bank
   if fix:
    span=(py-y)>>8;over=(125*65536-y)>>8
    q=min(32767,(over<<15)//span)
    curve+=dc*(q-32768)>>2
    sv=sine(abs(bank));step=((sv*80>>8)*scale)>>8
    step=((step>>8)*q)>>7
    x+= -step if bank<0 else step
  else:
   sv=sine(abs(curve));shift=s32(s16(sv*80>>8)*scale)>>8
   x+= -shift if curve<0 else shift
   prod=lane*scale;x+=(prod>>2)-(prod>>4)
  curve+= (dc*partial*2 if partial else dc<<16)>>3
  high=max(-90,min(90,s16(curve>>16)));curve=(high<<16)|(curve&65535)
  if heights:
   coeff=(scale*partial*2>>16) if partial else scale
   coeff=s16((0x48000-coeff*4)>>4)
   slope+= (s16(desc[2]<<8)>>8)*coeff
   bound=limits[row]<<16
   if row:bound+=(limits[row-1]-limits[row])*f
   slope=max(-bound,min(bound,slope))
  scale=scale*59637>>16;partial=0
 return (x,y,scale),rows
if __name__=='__main__':
 for name,segment,fix in [('curve-before',202,False),('curve-next-before',203,False),('curve-candidate',202,True),('curve-next-candidate',203,True)]:
  for p in (ROOT/'tmp/corner-jump'/name).glob('frame-*.bin'):
   b=p.read_bytes();expected,_=model(segment,u(b,-22338),fix=fix);actual=(l(b,-29844),l(b,-29848),u(b,-29852));assert expected[::2]==actual[::2],(name,p,expected,actual)
 print('Native model matches all four phase sweeps')
 for bank in [0,65536,5*65536]:
  for seg in [30,100,202,385,210]:
   for fix in [False,True]:
    a=model(seg,65535,bank=bank,fix=fix)[1];z=model(seg+1,0,bank=bank,fix=fix)[1]
    err=max(abs(a[i+1][0]-z[i][0])/65536 for i in range(8,39))
    print(seg,bank/65536,fix,err)
