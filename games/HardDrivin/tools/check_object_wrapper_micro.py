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

write(0x10000,Path('tmp/object-wrapper-micro.bin').read_bytes())
write(0x20032,Path('tmp/object-stub-micro.bin').read_bytes())
count=0
try:
 for active in [0,1]:
  for xflag in [0,16]:
   for projection in [(0,0,0),(1,0,0),(0,1,0),(0,0,-1)]:
    for oldobj in [0x34560,0x34590]:
     write(0x17000,struct.pack('>4IB3xI',100,9,13,9,255,oldobj))
     write(0x17040,bytes(32));pack(0x17048,'I',10);write(0x17058,bytes([active]));pack(0x17080,'I',105)
     write(0x31000,bytes(12));pack(0x2191e,'3h',*projection)
     reg(17,0x2000|xflag)
     for k in range(1,17):reg(k,k*0x10101)
     reg(4,0x34560);reg(5,0x28000);reg(8,0x4fff0)
     saved=[reg(k) for k in range(1,17)]
     emit=not active or oldobj!=0x34560 or any(projection)
     ok(u.uc_emu_start(h,0x10000,0x20000,1000000,1000))
     assert reg(8)==0x4fff0
     assert all(reg(k)==saved[k-1] for k in range(1,17) if k!=9)
     assert reg(9)==(85 if emit else saved[8])
     event,unused,calls,ccr=struct.unpack('>HHIH',read(0x31000,10))
     assert calls==int(emit) and event==(7 if emit else 0)
     assert ccr&16==(0 if emit else xflag)
     if not active:assert read(0x17000,24)==struct.pack('>4IB3xI',100,9,13,9,255,oldobj)
     count+=1
 result=dict(passed=True,actual_68000_wrapper_cases=count,register_stack_x_and_event_verified=True)
 Path('tmp/object-wrapper-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
