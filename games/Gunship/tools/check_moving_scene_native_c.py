"""Verify trajectory references against original clamp/control/motion slices."""
from unicorn_b import *
from layout import locate
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/moving-scene.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/moving-scene.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def call(addr,args={}):
 for r,v in args.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(addr);assert c.rr(18)==0x90000
p=0x320000;out=0x320100;clone=0x300000;clamp=0x370000
call(sym('motion_preview_prepare'),{1:h[0],2:clone});assert c.rr(9)==0
c.put(clamp,c.get(h[0]+0x5756,0x24)+bytes.fromhex('4e75'))
report=json.loads((root/'tmp/c/moving-scene-comparison.json').read_text());count=0
for run in report['results']:
 b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);b[16]=run['config'];b[27]=128;b[57]=30;b[66]=28;c.put(p,b);previous=0
 name=run['scenario'];rate=run['rate']
 if name=='reversal':tape=[(1,1)]*3+[(-1,-1)]*3+[(0,0)]*4
 elif name=='pulse':tape=[(1,-1),(0,0),(-1,1),(0,0)]*2+[(0,0)]*2
 else:tape=[tuple(map(int,name.strip('()').split(',')))]*10
 for row in run['boundaries']:
  x,y=tape[(row['field']-1)//rate]
  c.put(p+12,struct.pack('>H',row['tick']));c.put(h[6]+0x4294,bytes([x&255,y&255]));c.put(h[0]+0x5524,bytes([previous&255]));previous=y
  call(clamp,{6:p});call(h[0]+0x5376);call(sym('motion_preview'),{1:p,2:out,3:clone})
  actual=bytearray(c.get(out,86));actual[12:14]=bytes(2)
  assert actual==bytes.fromhex(row['native']),(name,run['config'],rate,row['tick'])
  c.put(p,c.get(out,86));count+=1
print(dict(original_native_motion_boundaries=count,all_reference_records_match=True,excluded='world RNG and ground/contact effects'))
c.close()
