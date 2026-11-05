#!/usr/bin/env python3
"""Native angle equivalence and field-rate coupled heading/track responses."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;S=0x320000;ref=0x330000;seed=h[4]+0x3cc
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/heading.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/heading.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c.put(ref,c.get(h[0]+0x937c,0x116)+bytes.fromhex('4e75'));rng=random.Random(9470);impulse=0;calls=0
sb=lambda x:(x&255)-256 if x&128 else x&255
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def capture(handle,a,n,user):
 global impulse
 impulse=sb(c.rr(9))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,capture,None,ref+0x112,ref+0x112))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:S,2:p,**args})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 return c.rr(9)
count=0;seen=set()
def native_case(heading,track,roll,pitch,yaw,height,damage):
 global count,impulse
 b=bytearray(86);b[0x35]=heading;b[0x3d]=track;b[0x37]=roll&255;b[0x36]=pitch&255;b[0x3f]=yaw&255;b[15]=damage
 struct.pack_into('>H',b,0x1c,height);struct.pack_into('>H',b,12,count&65535);b[0x1b]=120;b[0x39]=20
 c.put(p,b);impulse=0;c.rw(8,0x8f000);c.rw(6,p);c.rw(17,0x2000);c.call(ref)
 assert c.rr(18)==0x90000
 expected=c.get(p,86);rng_after=c.get(seed,4);seen.add(impulse)
 b[0x38]=expected[0x38];c.put(p,b)
 assert call('heading_init',{9:3})==0
 assert call('heading_step',{9:heading,10:track,11:impulse&0xffffffff})==0
 assert c.get(p,86)==expected,(heading,track,roll,pitch,yaw,height,damage,impulse)
 assert c.get(S,20)==struct.pack('>H',3)+bytes(18) and c.get(seed,4)==rng_after
 count+=1
for heading,track in itertools.product(range(256),repeat=2):native_case(heading,track,[-20,0,20][(heading+track)%3],5,3,512,(heading+track)%4)
for heading,yaw,roll,pitch in itertools.product(range(256),[-128,-4,-1,0,1,4,127],[-128,-20,0,20,127],[0,-1,-2,-3]):native_case(heading,(heading*13)&255,roll,pitch,yaw,512,1)
for n in range(1024):native_case(rng.randrange(256),rng.randrange(256),rng.randrange(-128,128),rng.randrange(-128,128),rng.randrange(-128,128),0,3)
assert seen=={-2,-1,0,1,2},seen
D=32767;gains={(50,2):0x230bc42,(50,4):0x7ea380,(60,2):0x1d3f349,(60,4):0x6990f7}
def response(error,own,target,rate,shift):
 if (error+(1<<(shift-1)))>>shift==0:return 0,own
 gain=gains[rate,shift];prod=lambda x:trunc(x*gain,65536)
 total=prod(error)+own-trunc(prod(own),D)+trunc(prod(target),D);q=trunc(total,D)
 return q,total-q*D
def linear(delta,main,conv,rate):
 a=delta*3;qi=trunc(a,rate);r=a-qi*rate
 u=r*D+conv;qf=trunc(u,rate);conv=u-qf*rate
 t=main+qf;qc=trunc(t,D)
 return qi+qc,t-qc*D,conv
field_cases=0
for n in range(12000):
 rate=rng.choice([50,60]);heading=rng.randrange(256);track=rng.randrange(256);roll=rng.randrange(-20,21);pitch=rng.choice([-3,0,1,20]);yaw=rng.randrange(-4,5);imp=rng.randrange(-2,3)
 hm,tm=[rng.randrange(-D+1,D) for _ in range(2)];hc,tc=[rng.randrange(-rate+1,rate) for _ in range(2)]
 c.put(S,struct.pack('>HHiiii',rate,0,hm,hc,tm,tc));b=bytearray(86);b[0x1c]=2;b[0x35]=heading;b[0x3d]=track;b[0x37]=roll&255;b[0x36]=pitch&255;b[0x3f]=yaw&255;c.put(p,b)
 if ((-pitch)&255)<4:
  q,hm,hc=linear(sb(2*yaw),hm,hc,rate);nh=(heading+q)&255;nt=(nh+(64 if roll>0 else -64 if roll<0 else 0))&255;tm,tc=hm,hc
 else:
  bank=roll>>2;q,hm=response(sb(track-heading+8)-8,hm,tm,rate,4);s,hm,hc=linear(bank,hm,hc,rate);nh=(heading+q+s)&255
  q,tm=response(sb(nh-track+2)-2,tm,hm,rate,2);s,tm,tc=linear(bank,tm,tc,rate);nt=(track+q+s)&255;b[0x3f]=0
 b[0x35]=(nh+imp)&255;b[0x3d]=nt
 before_seed=c.get(seed,4)
 assert call('heading_step',{9:heading,10:track,11:imp&0xffffffff})==0
 assert c.get(p,86)==b and c.get(S,20)==struct.pack('>HHiiii',rate,0,hm,hc,tm,tc)
 assert c.get(seed,4)==before_seed;field_cases+=1
invalid=0
for offset,value in [(4,-32767),(12,32767),(8,-2147483648),(16,50)]:
 assert call('heading_init',{9:50})==0;c.put(S+offset,struct.pack('>i',value));before=(c.get(p,86),c.get(S,20))
 assert call('heading_step',{9:0,10:0,11:0})==0xffffffff and before==(c.get(p,86),c.get(S,20));invalid+=1
r=dict(native_h1_cases=count,field_model_cases=field_cases,heading_impulses=sorted(seen),invalid_state_cases=invalid,calls=calls,scope='heading/track component with native wrapping and supplied world impulses; no full-flight or native installation proof')
(root/'tmp/c/heading-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
