import ctypes as C,json,os,random,re,struct
from pathlib import Path
u=C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.dylib'))
P=C.c_void_p; U=C.c_uint64; Z=C.c_size_t; I=C.c_int
for name,args in [('uc_open',[I,I,C.POINTER(P)]),('uc_ctl',[P,C.c_uint32]),('uc_mem_map',[P,U,Z,C.c_uint32]),('uc_mem_write',[P,U,P,Z]),('uc_mem_read',[P,U,P,Z]),('uc_reg_write',[P,I,P]),('uc_reg_read',[P,I,P]),('uc_emu_start',[P,U,U,U,Z]),('uc_close',[P])]:
 f=getattr(u,name);f.argtypes=args;f.restype=I
u.uc_strerror.argtypes=[I];u.uc_strerror.restype=C.c_char_p
def ok(x):assert x==0,u.uc_strerror(x)
h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x10000,0x40000,7))
def write(a,b):ok(u.uc_mem_write(h,a,b,len(b)))
def read(a,n):b=C.create_string_buffer(n);ok(u.uc_mem_read(h,a,b,n));return b.raw
def reg(k,v=None):
 x=C.c_uint32(v or 0)
 if v is None:ok(u.uc_reg_read(h,k,C.byref(x)));return x.value
 ok(u.uc_reg_write(h,k,C.byref(x)))
def pack(a,fmt,*v):write(a,struct.pack('>'+fmt,*v))
def trunc(x):return abs(x)//65536*(-1 if x<0 else 1)
b=0x10000;state=0x30000;sp=0x4fff0;end=0x20000
write(b,Path('tmp/object-audio-micro.bin').read_bytes());rng=random.Random(617);count=0;immediate=0;suppressed=0
try:
 cases=[]
 for now in [0,1,7,8,9,100,0xfffffffc,0xffffffff]:
  for step in [0,1,2,10,0xffffffff]:
   for fall in [0,1,-1,50,32767,-32768]:
    for valid in [0,255]:
     cases.append((now,step,fall,(now-rng.choice([0,1,7,8,9,100]))&0xffffffff,(step-rng.choice([0,1,2]))&0xffffffff,valid))
 for now,step,fall,last,seen,valid in cases:
  obj=0x34560; oldobj=rng.choice([obj,0x34590]);write(state,struct.pack('>4IB3xI',last,seen,13,9,valid,oldobj))
  reg(17,0x2000)
  for k in range(1,17):reg(k,k*0x10101)
  reg(1,state);reg(4,obj);reg(8,sp);reg(9,now);reg(10,step);reg(11,fall&0xffff);pack(sp,'I',end)
  saved=[reg(k) for k in range(1,17)]
  gap=(step-seen)&0xffffffff
  fresh=fall!=0 or obj!=oldobj
  due=fresh or not valid or gap>1 or (gap==1 and ((now-last)&0xffffffff)>=8)
  newlast=(now if fresh or not valid or gap>1 else (now-((now-last)&7))&0xffffffff) if due else last
  expected=(newlast,step,14,9+int(due),255 if due else valid,obj)
  ok(u.uc_emu_start(h,b,end,1000000,1000))
  assert reg(9)==int(due) and struct.unpack('>4IB3xI',read(state,24))==expected
  assert reg(8)==sp+4
  assert all(reg(k)==saved[k-1] for k in [1,2,3,4,5,6,7,13,14,15,16])
  count+=1;immediate+=fresh;suppressed+=not due
 result=dict(passed=True,actual_68000_cases=count,immediate_impulses_or_changed_objects=immediate,suppressed_sustained_requests=suppressed,preserved_registers_and_stack=True)
 Path('tmp/object-audio-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
