"""Native cockpit dirty counts and direct needle geometry ownership audit."""
from unicorn_b import *
from layout import locate
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c=CPU();c.put(0x200000,mem)
rng=random.Random(0xab20);counts=h[0]+0xb04c;record=0x180000;needle=h[0]+0xaf8c;drawstate=h[6]+0x38f6
# Blit and line writers are intentionally stubbed. Count calls, retain arguments.
blit=h[0]+0x9274;line=h[0]+0x8548
assert blit==0x98ef4c and line==0x98e220
for a in (blit,line):c.put(a,bytes.fromhex('4e75'))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
draws=[]
@CODE
def drawn(handle,a,n,user):draws.append((a,tuple(c.rr(9+i)&65535 for i in range(7)),c.get(drawstate+6,8)))
hooks=[]
for a in (blit,line):
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,drawn,None,a,a));hooks.append(hook)
def call(off,rs={}):
 c.rw(17,0x2000)
 for r,v in rs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(h[0]+off);assert c.rr(18)==0x90000
# Eight restore descriptors each use a dirty word. Two draws consume 2->1->0;
# any number of subsequent renders does no restore. No elapsed-time input.
restore_cases=0
for i in range(8):
 for n in (0,1,2):
  c.put(counts,bytes(18));ptr=counts+2+2*i;c.put(ptr,struct.pack('>H',n));c.put(record,struct.pack('>6H',3,4,5,6,0x0708,0))
  draws.clear()
  for k in range(6):
   call(0xab18,{2:ptr,3:record})
   assert int.from_bytes(c.get(ptr,2),'big')==max(0,n-k-1)
  assert len(draws)==n and all(x[0]==blit for x in draws);restore_cases+=1
# Native icon/text change paths arm exactly two repairs, using their index
# tables/descriptors. Stop before graphics setup; these are native instructions.
writer_cases=0
for icon in range(32):
 c.put(counts,bytes(18));c.rw(17,0x2000);c.rw(9,icon);c.rw(8,0x8f000)
 c.call(h[0]+0xaf36,end=h[0]+0xaf5a);assert c.rr(18)==h[0]+0xaf5a
 index=c.get(h[0]+0xafa4+icon,1)[0];expected=bytearray(18);expected[index:index+2]=b'\0\2'
 assert c.get(counts,18)==expected;writer_cases+=1
for offset in range(0,18,2):
 c.put(counts,bytes(18));c.put(record,bytes(12)+struct.pack('>H',offset));c.rw(17,0x2000);c.rw(1,record);c.rw(9,123);c.rw(8,0x8f000)
 c.call(h[0]+0xb0a6,end=h[0]+0xb0d4);assert c.rr(18)==h[0]+0xb0d4
 expected=bytearray(18);expected[offset:offset+2]=b'\0\2'
 assert c.get(counts,18)==expected and c.get(record+10,2)==b'\0{';writer_cases+=1
# Every angle and both physical buffers: native needle line comes directly
# from the current angle and fixed lookup table, independent of previous tip.
needle_cases=0
for slot in (0,1):
 for angle in range(256):
  c.put(h[6]+0x4bb0,struct.pack('>H',slot));buf=bytearray(rng.randbytes(24));buf[slot]=80;buf[6+slot]=90;c.put(record,buf);draws.clear()
  call(0xad30,{3:record,9:angle})
  idx=(angle*2)&126
  if angle&64:idx^=126
  xy=c.get(h[0]+0xafc4+idx,2)
  x=80+(-xy[0] if angle&128 else xy[0]);y=90+(-xy[1] if (angle-64)&128 else xy[1])
  assert len(draws)==1 and draws[0][0]==line
  assert draws[0][2]==struct.pack('>4H',80,90,x,y),(slot,angle,draws[0],x,y)
  want=bytearray(buf);want[12+slot]=x&255;want[18+slot]=y&255
  assert c.get(record,24)==want
  # Repeated draw has identical geometry despite cached endpoint changes.
  prior=draws[0];draws.clear();call(0xad30,{3:record,9:angle});assert draws==[prior]
  needle_cases+=1
print(json.dumps(dict(status='passed',dirty_restore_cases=restore_cases,dirty_writer_cases=writer_cases,direct_needle_cases=needle_cases,scope='drawing arguments and caches; graphics writers stubbed')));c.close()
