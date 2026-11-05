import sys,json,struct,collections
from harness_a import *
from drive import barto
s=Session(sys.argv[1]);rows=[]
def entry_value():
 raw=read_bytes(s,0x8000,6)
 if raw[:2]!=bytes.fromhex('4ef9'):
  print('raw',raw.hex(),flush=True); return 0
 v=int.from_bytes(raw[2:],'big')
 if 0x200000<=v<0xa00000 or v>=0x1000000:
  raw=read_bytes(s,v,6)
  assert raw[:2]==bytes.fromhex('4ef9')
  return int.from_bytes(raw[2:],'big')-v+0x8000
 return v
def capture(name,lo,hi):
 if name=='title':
  exp=rd(s,0x8002)-0x5000
  ptr=rd(s,exp+0x42000+0x6774)
  assert ptr==exp+0x28000,hex(ptr)
  assert read_bytes(s,ptr,61500)==read_bytes(s,0x18000,61500)
  samples=struct.unpack('>31I',read_bytes(s,exp+0x42000+0x67fc,124))
  assert all(p<0x100000 for p in samples),samples
  (s.out/'boot-music.json').write_text(json.dumps(dict(public=hex(ptr),samples=[hex(p) for p in samples]),indent=2))
 if name=='intro':
  exp=rd(s,0x8002)-0x5000;ptr=rd(s,exp+0x5012)
  assert ptr==exp+0x4ef80,hex(ptr)
  assert rd(s,ptr,2)==11
  addresses=[(ptr+rd(s,ptr+2+i*8))&0xffffffff for i in range(11)]
  assert all(a<0x100000 for a in addresses),addresses
  (s.out/'picture-index.json').write_text(json.dumps(dict(public=hex(ptr),pictures=[hex(a) for a in addresses]),indent=2))
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
  print('entry',i,hex(entry),flush=True)
  if entry==0x12896:break
  s.cmd('monitor fields 49')
 else:
  print(s.cmd('maintenance flush register-cache'),flush=True); print(s.cmd('info registers'),flush=True); print(s.cmd('x/20i $pc'),flush=True); raise RuntimeError('title not loaded')
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
 main=s.public_main_base;exp=main-0x5000
 fx=rd(s,0xb6106); assert fx==exp+0x4e000,hex(fx)
 native=0x11a7e; size=rd(s,native); assert size in (0x40,0x58); fx_data=read_bytes(s,fx,size); fx_samples=[(fx+int.from_bytes(fx_data[i:i+4],'big'))&0xffffffff for i in range(0,size,8)]; assert fx_samples==[native+rd(s,native+i) for i in range(0,size,8)],fx_samples
 (s.out/'fx.json').write_text(json.dumps(dict(public=hex(fx),samples=fx_samples),indent=2))
 ptr=rd(s,0xb5958); assert ptr==exp+0x5c000,hex(ptr)
 sample_ptrs=struct.unpack('>31I',read_bytes(s,0xb59e0,124)); assert all(p<0x100000 for p in sample_ptrs),sample_ptrs
 (s.out/'music.json').write_text(json.dumps(dict(public=hex(ptr),samples=[hex(p) for p in sample_ptrs]),indent=2))
 raw=read_bytes(s,exp+0x49000,0x4020)
 assert raw[:16]==bytes.fromhex('a55aa55a')*4 and raw[-16:]==bytes.fromhex('a55aa55a')*4
 first=next((i for i in range(0,0x4000,4) if raw[16+i:20+i]!=bytes.fromhex('a55aa55a')),0x4000)
 (s.out/'boot-stack.json').write_text(json.dumps(dict(base=hex(exp+0x49010),top=hex(exp+0x4d010),observed_used=0x4000-first),indent=2)+'\n')
 (s.out/'dma.json').write_text(json.dumps(rows,indent=2)+'\n')
finally:s.quit()
