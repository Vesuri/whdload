"""Model native ascending CA bitmap/mask blits with exact word shifters."""
import json,struct,sys
from pathlib import Path
def render(c,before,mask,sources):
 b=bytearray(before);w=c['width'];h=c['height'];shift=c['shift'];con=c['con0'];assert con&255==0xca,hex(con)
 groups=[]
 if not con&32:groups.append((c['zero_planes'],None,0))
 if con&64:groups.append((c['one_planes'],None,65535))
 groups.extend((planes,s,0) for planes,s in zip(c['source_planes'],sources))
 for planes,source,constant in groups:
  for plane in range(4):
   if not planes&c['plane_mask']&(1<<plane):continue
   ap=bp=0;dst=plane*8000+c['dest_offset'];pa=pb=0
   for row in range(h):
    for x in range(w):
     # No mask and no shift disables A DMA/shifter entirely.
     if mask is None and shift==0:a=65535
     else:
      av=struct.unpack_from('>H',mask,ap)[0] if mask is not None else 65535
      if x==0:av&=c['afwm']
      if x==w-1:av&=c['alwm']
      a=((pa<<16)|av)>>shift&65535;pa=av
     if source is None:bb=constant
     else:
      bv=struct.unpack_from('>H',source,bp)[0];bb=((pb<<16)|bv)>>shift&65535;pb=bv
     old=struct.unpack_from('>H',b,dst)[0];struct.pack_into('>H',b,dst,(a&bb)|((a^65535)&old));ap+=2;bp+=2;dst+=2
    ap+=c['amod'];bp+=c['bmod'];dst+=c['dmod']
 return bytes(b)
if __name__=='__main__':
 failures=[];total=0
 for arg in sys.argv[1:]:
  p=Path(arg);cases=json.loads((p/'cases.json').read_text())
  for i,c in enumerate(cases):
   def rd(s):return (p/f'{i:03}-{s}.bin').read_bytes()
   expected=render(c,rd('before'),rd('mask') if c['has_mask'] else None,[rd(f'source{j}') for j in range(len(c['source_planes']))]);actual=rd('after');n=sum(x!=y for x,y in zip(expected,actual));total+=1
   if n:failures.append({'case':i,'path':str(p),'different_bytes':n,'first_diff':next(j for j,(x,y) in enumerate(zip(expected,actual)) if x!=y)})
 print(json.dumps({'cases':total,'failures':failures},indent=2));assert not failures
