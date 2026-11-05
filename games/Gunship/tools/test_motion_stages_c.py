#!/usr/bin/env python3
"""Native staged execution must equal the whole deterministic motion preview."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/motion-stages.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/motion-stages.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
whole=0x300000;stages=0x310000;p=0x320000;out=0x320100;terms=0x320200;rng=random.Random(9492)
def call(name,ptrs):
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(ptrs)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name))
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('motion_preview_prepare',{1:h[0],2:whole})==0
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
coordinate_ref=0x330000
ref=bytearray(c.get(whole,0x41e));ref[0x382:0x384]=bytes.fromhex('4e75');c.put(coordinate_ref,ref)
fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text());checks=0
sword=lambda x:x-65536 if x&32768 else x
word=lambda off:int.from_bytes(c.get(p+off,2),'big')
for n in range(int(os.environ.get('GS_STAGE_CASES','4096'))):
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input'])
 if n>=384:struct.pack_into('>H',b,28,n%34)
 c.put(p,b);call('motion_preview',{1:p,2:out,3:whole});expected=c.get(out,86)
 c.put(p,b);c.put(terms,bytes(12))
 for stage in range(7):
  before=c.get(p,86)
  assert call('motion_stage',{1:p,2:stages,3:terms,9:stage})==0
  t=struct.unpack('>III',c.get(terms,12))
  if stage==1:
   target=sword(t[0]&65535);old=sword(t[1]&65535)
   delta=sword((target-old+2)&65535)>>2
   assert c.get(p+0x3e,1)[0]==(old+delta)&255
  if stage==3:
   assert c.get(p,86)==before
   error=sword(t[0]&65535);slew=sword(t[1]&65535)
   oldspeed=word(0x2a)
   new_speed=(oldspeed+(sword((error+8)&65535)>>4)+slew)&65535
  if stage==4:assert word(0x2a)==new_speed
 assert c.get(p,86)==expected,n
 checks+=1
# A caller-adjusted speed must replace the preceding slice's whole-tick d0.
speed_checks=0
for speed in [-32768,-129,-128,-1,0,1,127,128,255,32767]:
 for altitude in [0,1,64,2000]:
  b=bytearray.fromhex(fixtures[speed_checks]['input'])
  struct.pack_into('>H',b,0x2a,speed&65535);struct.pack_into('>H',b,0x1c,altitude)
  c.put(p,b);c.rw(8,0x8f000);c.rw(6,p);c.rw(9,speed&0xffffffff)
  c.call(coordinate_ref+0x2f6);assert c.rr(18)==0x90000
  expected=c.get(p,86);c.put(p,b);c.put(terms,bytes.fromhex('123456789abcdef001020304'))
  assert call('motion_stage',{1:p,2:stages,3:terms,9:5})==0
  assert c.get(p,86)==expected
  speed_checks+=1
# Invalid stage must leave record, terms and prepared code intact.
for stage in [7,8,65535,0xffffffff]:
 saved=[c.get(p,86),c.get(terms,12),c.get(stages,sym('MS_CODE_SIZE'))]
 assert call('motion_stage',{1:p,2:stages,3:terms,9:stage})==0xffffffff
 assert saved==[c.get(p,86),c.get(terms,12),c.get(stages,sym('MS_CODE_SIZE'))]
r=dict(native_preview_comparisons=checks,stage_calls=checks*7,invalid_stage_cases=4,adjusted_speed_cases=speed_checks,scope='seven native slices equal whole deterministic preview; vertical and forward response terms verified; not scaled field integration')
(root/'tmp/c/motion-stages-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
