#!/usr/bin/env python3
"""Check native preview equivalence and write isolation, including contact paths."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/motion-preview.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/motion-preview.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x310000;out=0x320000;size=0x41e;rng=random.Random(9376)
def call(name,ptrs):
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(ptrs)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name))
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,name
 for r,v in regs.items():
  if name=='motion_preview_prepare' and r==9:continue
  assert c.rr(r)==v,(name,r)
 return c.rr(9)
original=c.get(h[0]+0x937c,size)
# Every validated instruction/target must fail closed before destination writes.
checks=[0,0xf8,0xfc,0x224,0x41c,0x104,0x106,0x26c,0x26e]
for o in [0x14e,0x180,0x1a0,0x2c6,0x304,0x33c]:checks.extend([o,o+2])
for off in checks:
 a=h[0]+0x937c+off;old=c.get(a,1);c.put(a,bytes([old[0]^1]));c.put(clone,b'\xa5'*size)
 assert call('motion_preview_prepare',{1:h[0],2:clone})==0xffffffff
 assert c.get(clone,size)==b'\xa5'*size
 c.put(a,old)
assert call('motion_preview_prepare',{1:h[0],2:clone})==0
assert c.get(h[0]+0x937c,size)==original
expected=bytearray(original);expected[0xf8:0xfc]=bytes.fromhex('6000001c');expected[0x224:0x228]=bytes.fromhex('60000094')
assert c.get(clone,size)==expected
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
previewing=False;reference_skip=False;badwrites=[];ground_visits=0
@MEM
def watch(handle,kind,a,n,value,user):
 if previewing and not (out<=a and a+n<=out+86 or 0x8d000<=a and a+n<=0x90000):badwrites.append((a,n))
@CODE
def skip(handle,a,n,user):
 global ground_visits
 if reference_skip and a==h[0]+0x9474:c.rw(18,h[0]+0x9492)
 if reference_skip and a==h[0]+0x95a0:
  ground_visits+=1;c.rw(18,h[0]+0x9636)
hooks=[]
for typ,cb in [(1<<11,watch),(1<<2,skip)]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),typ,cb,None,1,0));hooks.append(hook)
fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text());count=0
for n in range(4096):
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input'])
 if n<384:
  # Independent, unmodified native airborne path, with no random impulse.
  b[15]&=0xfc;reference_skip=False
 else:
  # Reach zero-height paths; reference skips precisely the world-owned blocks.
  struct.pack_into('>H',b,28,n%34);reference_skip=True
 c.put(p,b);c.rw(8,0x8f000);c.rw(6,p);c.rw(5,h[6]);c.rw(17,0x2000);c.call(h[0]+0x937c)
 assert c.rr(18)==0x90000
 reference=c.get(p,86);c.put(p,b);c.put(out-2,b'\xaa\x55'+bytes(86)+b'\x55\xaa')
 previewing=True;call('motion_preview',{1:p,2:out,3:clone});previewing=False
 assert c.get(out,86)==reference,n
 assert c.get(p,86)==b and not badwrites,(n,badwrites)
 assert c.get(out-2,2)==b'\xaa\x55' and c.get(out+86,2)==b'\x55\xaa'
 count+=1
assert ground_visits>0
r=dict(cases=count,unmodified_airborne_cases=384,instrumented_reference_cases=count-384,ground_reference_visits=ground_visits,fail_closed_cases=len(checks),unexpected_preview_writes=badwrites)
(root/'tmp/c/motion-preview-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
