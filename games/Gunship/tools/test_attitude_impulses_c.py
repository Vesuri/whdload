#!/usr/bin/env python3
"""Capture native world impulses, then replay them through the attitude step."""
import itertools,json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;S=0x320000;seed=h[4]+0x3cc
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/attitude.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/attitude.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
rng=random.Random(5380);imp=[0,0];seen=set();checking=False;badwrites=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
sbyte=lambda n:(n&255)-256 if n&128 else n&255
@CODE
def capture(handle,a,n,user):
 if a==h[0]+0x538e:imp[0]=sbyte(c.rr(9))*4
 else:imp[1]=sbyte(c.rr(9))
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not (p<=a and a+n<=p+86 or S<=a and a+n<=S+12 or 0x8d000<=a and a+n<=0x90000):badwrites.append((a,n))
hooks=[]
for addr in [h[0]+0x538e,h[0]+0x53ea]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,capture,None,addr,addr));hooks.append(hook)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
def call(name,x,y,roll=0,pitch=0):
 global checking
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9)};regs.update({1:S,2:p,10:y&0xffffffff,11:roll&0xffffffff,12:pitch&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.rw(9,x&0xffffffff);checking=True;c.call(base+sym(name));checking=False
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items()) and not badwrites
 return c.rr(9)
count=0
for mode,damage,height,speed,x,y,previous,roll,pitch in itertools.product([0,1],[0,1],[0,1,128,255,256,512],[0,7,8,127,255],[-1,0,1],[-1,0,1],[-1,0,1],[-21,-20,-19,0,19,20,21],[-128,0,127]):
 b=bytearray(86);b[15]=damage;struct.pack_into('>H',b,12,count&65535);struct.pack_into('>H',b,28,height);struct.pack_into('>H',b,42,speed)
 b[54]=pitch&255;b[55]=roll&255;c.put(p,b);c.put(h[6]+0x45cc,bytes([mode]))
 c.put(h[6]+0x4294,bytes([x&255,y&255]));c.put(h[0]+0x5524,bytes([previous&255]));imp[:]=[0,0]
 c.rw(8,0x8f000);c.rw(6,p);c.rw(17,0x2000);c.call(h[0]+0x5376);assert c.rr(18)==0x90000
 expected=c.get(p,86);rng_after=c.get(seed,4);seen.add(tuple(imp));c.put(p,b)
 assert call('attitude_init',3,previous)==0
 assert call('attitude_step_impulses',x,y,*imp)==0
 assert c.get(p,86)==expected,(mode,damage,height,speed,x,y,previous,roll,pitch,imp)
 assert c.get(seed,4)==rng_after
 count+=1
assert seen==set(itertools.product([-4,0,4],[-1,0,1])),seen
# Whole impulses must retain their magnitude at field rates, including clamp ordering.
field_checks=0
for rate,roll,ri,pi in itertools.product([50,60],[-20,0,20],[-4,0,4],[-1,0,1]):
 b=bytearray(86);b[55]=roll&255;c.put(p,b);assert call('attitude_init',rate,0)==0
 before=c.get(seed,4);assert call('attitude_step_impulses',0,0,ri,pi)==0
 assert c.get(p+54,2)==bytes([pi&255,max(-20,min(20,roll+ri))&255])
 assert c.get(seed,4)==before;field_checks+=1
invalid=0
for ri,pi in [(-5,0),(-3,0),(1,0),(5,0),(0,-2),(0,2)]:
 before=(c.get(p,86),c.get(S,12),c.get(seed,4))
 assert call('attitude_step_impulses',0,0,ri,pi)==0xffffffff
 assert before==(c.get(p,86),c.get(S,12),c.get(seed,4));invalid+=1
r=dict(native_h1_cases=count,impulse_pairs=sorted(seen),field_impulse_cases=field_checks,invalid_cases=invalid,unexpected_writes=badwrites,scope='native attitude including captured RNG outcomes; generation/eligibility remain world-owned and are not installed')
(root/'tmp/c/attitude-impulse-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
