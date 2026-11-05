import sys,json,struct,collections
from harness_a import *
from drive import barto
s=Session(sys.argv[1]);rows=[]
def entry_value():
 if rd(s,0x8000,2)!=0x4ef9:return 0
 v=rd(s,0x8002)
 if 0x200000<=v<0xa00000 or v>=0x1000000:
  assert rd(s,v,2)==0x4ef9
  return rd(s,v+2)-v+0x8000
 return v
def capture(name,lo,hi):
 p=s.out/(name+'.bin');s.cmd(f'monitor profile 19 "" "{p}"',timeout=120);t=barto.load(str(p));seen=collections.defaultdict(set)
 for f in t.fields:
  for i in range(0,len(f.dma),f.dma_size):
   a=struct.unpack_from('<I',f.dma,i+12)[0];kind=struct.unpack_from('<h',f.dma,i+29)[0]
   if kind not in (0,2) and lo<=a<hi:seen[kind].add(a)
 (s.out/(name+'.png')).write_bytes(t.fields[-1].shot)
 r=dict(name=name,dma={str(k):[hex(min(v)),hex(max(v)),len(v)] for k,v in seen.items()});rows.append(r);print(r,flush=True)
try:
 for i in range(200):
  try:entry=entry_value()
  except (ValueError,IndexError):entry=0
  if entry==0x12896:break
  s.cmd('monitor fields 49')
 else:raise RuntimeError('title not loaded')
 s.cmd('monitor fields 199');capture('title',0x8000,0x17e86)
 for i in range(150):
  if entry_value()==0x8a68:break
  s.cmd('monitor fields 99')
 else:raise RuntimeError('intro not entered after waiting')
 s.cmd('monitor fields 199');capture('intro',0x8000,0xa008)
 for stage in range(1,8):
  s.cmd('monitor fields 299');capture(f'intro-{stage}',0x8000,0xa008)
 # Confirm that continuing past the intro still reaches a playable main race.
 route(s);s.shot('race.png')
 (s.out/'dma.json').write_text(json.dumps(rows,indent=2)+'\n')
finally:s.quit()
