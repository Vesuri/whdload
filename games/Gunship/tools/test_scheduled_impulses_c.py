#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-impulses.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/scheduled-impulses.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
whole=0x300000;stages=0x310000;p=0x320000;out=0x320100;terms=0x320200;state=0x320300;rng=random.Random(9636);calls=0
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
signed=lambda n:n-2**32 if n&2**31 else n
sb=lambda n:(n&255)-256 if n&128 else n&255
sw=lambda n:(n&65535)-65536 if n&32768 else n&65535
def call(name,ptrs):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(ptrs)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 for r,v in regs.items():
  if r==9 or r==10 and name=='fraction_add_rate':continue
  assert c.rr(r)==v,(name,r)
 return c.rr(9)
def long(off):return struct.unpack('>i',c.get(state+off,4))[0]
def qvalue(off,rate,conversion=None):return F(long(off),32767)+(F(long(conversion),rate*32767) if conversion else 0)
assert call('motion_preview_prepare',{1:h[0],2:whole})==0
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text())



TS=0x400000;TC=0x401000;TH=0x402000;CQ=0x404000;rec=0x405000;sample=0x406000;shadow=0x408000;packet=0x409000;context=0x420000
word=lambda a:int.from_bytes(c.get(a,2),'big')
SI=0x440000;RNG=0x441000;COUNT=0x442000
c.put(RNG,bytes.fromhex('52b9')+struct.pack('>I',COUNT)+bytes.fromhex('203c000000ff4e75'))
def ready():
 for name,args in [('clock_init',{1:TC,9:0,10:50}),('history_init',{1:TH,9:0}),('commands_init',{1:CQ,9:0}),('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})]:assert call(name,args)==0
 c.put(TS+12,struct.pack('>HH',1,1));c.put(TS+24,struct.pack('>II',17,0));c.put(rec,struct.pack('>I',17)+bytes(36))
 c.put(SI,struct.pack('>5I',TS,p,RNG,packet,rec)+bytes(18));c.put(COUNT,bytes(4));c.put(packet,struct.pack('>hhhhh',1,-1,0,0,0))
 b=bytearray(86);b[15]=1;struct.pack_into('>H',b,28,16);struct.pack_into('>H',b,42,32);c.put(p,b)
ready();before=c.get(p,86)
assert call('scheduled_motion_impulses',{1:SI})==0
assert c.get(COUNT,4)==struct.pack('>I',3) and word(SI+30)==1
assert c.get(packet,10)==struct.pack('>hhhhh',1,-1,4,1,2) and c.get(p,86)==before
c.put(packet+4,bytes(6));c.put(p+15,b'\0')
assert call('scheduled_motion_impulses',{1:SI})==1
assert c.get(COUNT,4)==struct.pack('>I',3) and word(SI+30)==0 and c.get(packet+4,6)==struct.pack('>hhh',4,1,2)
# Same field cannot change its retained command cutoff.
c.put(TS+28,struct.pack('>I',1));c.put(rec+20,struct.pack('>I',1))
assert call('scheduled_motion_impulses',{1:SI})==0xfffffffd and c.get(COUNT,4)==struct.pack('>I',3)
# Next delivered deadline admits a new generation; no disturbance is eligible.
c.put(TS+24,struct.pack('>II',34,1));c.put(rec,struct.pack('>I',34));c.put(p+28,bytes(2));c.put(p+42,bytes(2))
assert call('scheduled_motion_impulses',{1:SI})==0 and c.get(packet+4,6)==bytes(6)
assert c.get(COUNT,4)==struct.pack('>I',3)
for kind in ['phase','due','field','cutoff','fault']:
 ready()
 if kind=='phase':c.put(TS+12,struct.pack('>H',2))
 if kind=='due':c.put(TS+14,bytes(2))
 if kind=='field':c.put(rec,struct.pack('>I',18))
 if kind=='cutoff':c.put(rec+20,struct.pack('>I',1))
 if kind=='fault':c.put(TH+6,struct.pack('>H',1))
 before=c.get(packet,10),c.get(p,86)
 assert call('scheduled_motion_impulses',{1:SI})==(0xffffffff if kind=='fault' else 0xfffffffd)
 assert before==(c.get(packet,10),c.get(p,86)) and c.get(COUNT,4)==bytes(4) and word(SI+28)==0
for world_only in [False,True]:
 ready();assert call('commands_publish',{1:CQ,9:1,10:1})==1
 c.put(TS+28,struct.pack('>I',1));c.put(rec+20,struct.pack('>I',1))
 if world_only:c.put(CQ+2,struct.pack('>H',1))
 before=c.get(CQ,1048),c.get(packet,10)
 assert call('scheduled_motion_impulses',{1:SI})==0xfffffffd
 assert before==(c.get(CQ,1048),c.get(packet,10)) and c.get(COUNT,4)==bytes(4)
# Fault during RNG: the finished cache survives; recovery reuses it.
c.close();c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-impulses.hunk')).get_segments()[0].get_data()))
c.put(RNG,bytes.fromhex('52b9')+struct.pack('>I',COUNT)+bytes.fromhex('203c000000ff4e75'));ready()
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def fault(handle,a,n,user):c.put(TH+6,struct.pack('>H',1))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,RNG,RNG))
assert call('scheduled_motion_impulses',{1:SI})==0xffffffff
assert word(SI+28)==word(SI+30)==1 and c.get(COUNT,4)==struct.pack('>I',3)
assert c.get(SI+32,6)==struct.pack('>hhh',4,1,2)
c.put(TH+6,bytes(2));c.put(TS+22,bytes(2));c.put(packet+4,bytes(6))
assert call('scheduled_motion_impulses',{1:SI})==1
assert c.get(COUNT,4)==struct.pack('>I',3) and c.get(packet+4,6)==struct.pack('>hhh',4,1,2)
print(dict(three_draws_once=True,cached_retry=True,fault_cache_retained=True,rejections=7,calls=calls));c.close()
