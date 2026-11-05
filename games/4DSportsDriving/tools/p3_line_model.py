"""Native clipped line stepping (all octants), from BLTAPT error recurrence."""
import json,sys
from pathlib import Path
def render(c,before):
 b=bytearray(before);x,y,xe,ye=c['xy'];dx=abs(xe-x);dy=abs(ye-y);sx=1 if xe>=x else -1;sy=1 if ye>=y else -1
 major=max(dx,dy);minor=min(dx,dy);error=2*minor-major
 for _ in range(major+1):
  assert 0<=x<320 and 0<=y<200
  for plane in range(4):
   if not c['write_mask']&(1<<plane):continue
   at=plane*8000+y*40+x//8;mask=128>>(x&7)
   b[at]=(b[at]|mask) if c['colour']&(1<<plane) else b[at]&(255^mask)
  if error>=0:
   if dx>=dy:y+=sy
   else:x+=sx
   error-=2*major
  if dx>=dy:x+=sx
  else:y+=sy
  error+=2*minor
 return bytes(b)
if __name__=='__main__':
 for arg in sys.argv[1:]:
  p=Path(arg);cases=json.loads((p/'cases.json').read_text());bad=[]
  for i,c in enumerate(cases):
   expected=render(c,(p/f'{i:03}-before.bin').read_bytes());actual=(p/f'{i:03}-after.bin').read_bytes();diff=sum(a!=b for a,b in zip(expected,actual))
   if diff:bad.append((i,c['xy'],diff))
  print(json.dumps({'path':str(p),'cases':len(cases),'failed':bad},indent=2));assert not bad
