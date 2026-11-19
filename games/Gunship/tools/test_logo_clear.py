"""Execute the assembled logo_clear (logo-clear.i) of both release slaves.

With the title's RectFill arguments it zeroes rows 50..148 of every plane and
nothing else, without calling RectFill, and returns d3 = 148 as the replaced
code did. Any other layout falls back to RectFill once, with the original
arguments. Both paths preserve d2/d4-d7/a1-a6. The beam wait needs the
chipset; docs/development.md records how it was checked in the emulator.
"""
from unicorn_b import *
import random

G=0x400000;VIEW=0x410000;VP=0x420000;BM=0x430000;RP=0x440000;PLANES=0x100000;CALLS=0x600000
def L(v):return struct.pack('>I',v)
def W(v):return struct.pack('>H',v)
rng=random.Random(149);total=0
for name in ('Gunship','GunshipNTSC'):
 f=build/'release'/f'{name}.Slave'
 s={}
 for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',f.with_suffix('.lst').read_text(encoding='latin1'),re.M):s.setdefault(n,int(v,16))
 blob=bytes(BinFmt().load_image(str(f)).get_segments()[0].get_data())
 cases=[('title',{})]+[(k,{k:1}) for k in ('layer','x0','x1','width','depth0','depth9','rows','y0','view','viewport')]
 for label,bad in cases:
  c=CPU();c.put(base,blob)
  c.put(G-228,bytes.fromhex('4e75')) # WaitBlit
  c.put(G-306,bytes.fromhex('52b9'+'00600000'+'4e75')) # RectFill: count the call
  c.put(G+34,L(0 if bad.get('view') else VIEW))
  c.put(VIEW,L(0 if bad.get('viewport') else VP));c.put(VIEW+12,W(0x2c));c.put(VP+30,W(0))
  c.put(0xdff004,L(0)) # beam on line 0, far from rows 94..192
  depth=0 if bad.get('depth0') else 9 if bad.get('depth9') else 5
  c.put(BM,W(80 if bad.get('width') else 40)+W(140 if bad.get('rows') else 200)+bytes([0,depth,0,0]))
  for p in range(8):c.put(BM+8+4*p,L(PLANES+p*0x2000))
  planes=bytes(rng.randrange(1,256) for _ in range(8*0x2000));c.put(PLANES,planes)
  c.put(RP,L(1 if bad.get('layer') else 0)+L(BM))
  args={9:1 if bad.get('x0') else 0,10:149 if bad.get('y0') else 50,11:318 if bad.get('x1') else 319,12:rng.randrange(1<<32)}
  regs={r:rng.randrange(1<<32) for r in (13,14,15,16,1,3,4,5,6)};regs.update({2:RP,7:G});regs.update(args)
  for r,v in regs.items():c.rw(r,v)
  c.call(base+s['logo_clear'])
  calls=struct.unpack('>I',c.get(CALLS,4))[0];after=c.get(PLANES,8*0x2000)
  assert c.rr(12)==148,(name,label)
  keep=[11,13,14,15,16,2,3,4,5,6,7] # d2, d4-d7, a1-a6
  assert all(c.rr(r)==regs[r] for r in keep),(name,label,'registers')
  if label=='title':
   assert calls==0,(name,label)
   exp=bytearray(planes)
   for p in range(5):exp[p*0x2000+50*40:p*0x2000+149*40]=bytes(99*40)
   assert after==bytes(exp),(name,label)
  else:
   assert calls==1 and after==planes,(name,label,calls)
   assert (c.rr(9),c.rr(10),c.rr(11))==(args[9],args[10],args[11]),(name,label,'arguments')
  c.close();total+=1
print(f'PASS {total} logo_clear cases: rows 50..148 of each plane only, RectFill fallbacks, registers')
