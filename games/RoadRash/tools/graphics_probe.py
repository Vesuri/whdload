import sys,json,struct,collections
from harness_a import *
from drive import barto
s=Session(sys.argv[1])
try:
 for i in range(1500):
  try:p=rd(s,0x81e70)
  except (ValueError,IndexError):p=0
  if hasattr(s,'public_main_base') and 0x200000<=p<0xa00000:break
  s.input('JOY2_FIRE_BUTTON',int(i%4==0));s.cmd('monitor fields 4')
 else:raise RuntimeError('public menu not reached')
 s.input('JOY2_FIRE_BUTTON',0);exp=s.public_main_base-0x5000
 joy=rd(s,0x4e6);assert joy==exp+0x4e180,hex(joy);assert rd(s,0x4f2)==2224
 first=p-2;second=rd(s,0x81d60)+rd(s,0x4ee)
 assert first==exp+0x4e080 and second==exp+0x4e100,(hex(first),hex(second))
 rows=[]
 for ptr,orig in [(first,0xda7e),(second,0xda7e+rd(s,0x4ee))]:
  n=rd(s,ptr,2);size=2+14*n;assert 0<n<=9
  assert read_bytes(s,ptr,size)==read_bytes(s,orig,size)
  rows.append(dict(public=hex(ptr),original=hex(orig),count=n))
 s.cmd('monitor fields 299');s.shot('menu-settled.png')
 tracepath=s.out/'menu.bin';s.cmd(f'monitor profile 99 "" "{tracepath}"',timeout=120);trace=barto.load(str(tracepath));hits=[]
 for f in trace.fields:
  for i in range(0,len(f.dma),f.dma_size):
   a=struct.unpack_from('<I',f.dma,i+12)[0];kind=struct.unpack_from('<h',f.dma,i+29)[0]
   if kind not in (0,2) and exp+0x4e080<=a<exp+0x4e180:hits.append((a,kind))
 assert not hits,hits
 (s.out/'menu.png').write_bytes(trace.fields[-1].shot)
 (s.out/'headers.json').write_text(json.dumps(rows,indent=2))
 route(s);s.shot('race.png')
 sets=[]
 for address in (0xb9108,0xb9c90,0xba2a0,0xbab02,0xbad72):
  count=rd(s,address,2)
  pixels=[rd(s,address+2+14*i) for i in range(count)]
  assert all(address < p < 0xbc3ec for p in pixels),(hex(address),pixels)
  sets.append(dict(address=hex(address),count=count,pixels=[hex(p) for p in pixels]))
 (s.out/'embedded-pointers.json').write_text(json.dumps(sets,indent=2))
 s.input('JOY2_UP',1)
 for target in (500,1000,2000):
  advance(s,target);s.shot(f'race-{target}.png')
finally:s.quit()
