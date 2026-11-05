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
b=0x10000;a4=0x30000;sp=0x4fff0;native=0x2b9c0
sy={n:b+int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',Path('tmp/manual-dispatch-micro.lst').read_text(),re.M)}
write(b,Path('tmp/manual-dispatch-micro.bin').read_bytes());count=deferred=0
try:
 for active in [0,1,2]:
  for original in [0,1,8,14,65535]:
   for remaining in [0,1,8,14,65535]:
    for request in [0,1,2,4,5]:
     for joystick in [0,1,4,255]:
      state=struct.pack('>4H2I',original,remaining,0,active,17,9);write(sy['_drivetrain_state'],state)
      pack(a4-0x66e3,'B',request);pack(a4-0x6a01,'B',joystick)
      reg(17,0x2000)
      for k in range(1,17):reg(k,k*0x10101)
      reg(5,a4);reg(8,sp);pack(sp,'I',native);saved=[reg(k) for k in range(1,17)]
      later=active==1 and original!=remaining;target=0x2ba8a if later else (0x2b9c8 if request else native)
      ok(u.uc_emu_start(h,b,target,1000000,1000));assert reg(18)==target
      assert [reg(k) for k in range(1,17) if k!=8]==[saved[k-1] for k in range(1,17) if k!=8]
      assert reg(8)==sp+4
      assert read(sy['_drivetrain_state'],16)==state
      assert read(a4-0x66e3,1)==bytes([request]) and read(a4-0x6a01,1)==bytes([joystick])
      count+=1;deferred+=later and bool(request or joystick)
 result=dict(passed=True,actual_68000_dispatch_cases=count,deferred_nonzero_requests_preserved=deferred,registers_and_stack_preserved=True)
 Path('tmp/manual-dispatch-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
