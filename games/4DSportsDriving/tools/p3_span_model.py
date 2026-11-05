"""Exact native clipped span model; no 68k replacement until captures agree."""
import json,sys
from pathlib import Path
def render(c,before):
 b=bytearray(before)
 for row,(left,right) in enumerate(c['spans']):
  # Native solid packed writer uses strict high-word comparison only when
  # the preceding low-word span is empty; preserve this native edge quirk.
  # The trailing height%8 rows use scalar writes and include equal endpoints.
  if (c['kind']=='solid' and left==right and row<c['height']//8*8
      and row%2==0 and c['spans'][row+1][0]>c['spans'][row+1][1]):continue
  for x in range(left,right+1):
   assert 0<=x<320 and 0<=row+c['y']<200
   bit=32768>>(x&15)
   if c['kind']=='solid':
    if c['stipple']:
     pat=(c['stipple_pattern']>>(16*(1-(c['height']-1-row)%2)))&65535
     if not pat&bit:continue
    colour=c['colour']
   else:
    pat=(c['pattern']>>(16*(1-row%2)))&65535
    colour=c['colour'] if pat&bit else c['colour2']
   for plane in range(4):
    if not c['write_mask']&(1<<plane):continue
    j=plane*8000+(row+c['y'])*40+x//8; mask=128>>(x&7)
    b[j]=(b[j]|mask) if colour&(1<<plane) else (b[j]&(255^mask))
 return bytes(b)
if __name__=='__main__':
 report=[]
 for arg in sys.argv[1:]:
  p=Path(arg);cases=json.loads((p/'cases.json').read_text())
  for i,c in enumerate(cases):
   actual=(p/f'{i:03}-after.bin').read_bytes();expected=render(c,(p/f'{i:03}-before.bin').read_bytes());diff=sum(a!=b for a,b in zip(actual,expected))
   report.append({'path':str(p),'case':i,'kind':c['kind'],'stipple':c['stipple'],'different_bytes':diff,'plane_bytes_compared':32000})
 print(json.dumps({'cases':len(report),'failed':[r for r in report if r['different_bytes']],'kinds':sorted(set(r['kind'] for r in report))},indent=2))
 assert all(not r['different_bytes'] for r in report)
