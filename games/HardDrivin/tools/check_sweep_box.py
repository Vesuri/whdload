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

from fractions import Fraction
write(0x10000,Path('tmp/sweep-box.bin').read_bytes())
rng=random.Random(39127)
cases=[[(0,0,-30,30),(0,0,-30,30),(100,-50,3,77)],[(100,-50,-30,30),(-100,50,-30,30),(100,-50,3,77)]]
for i in range(10000):
 axes=[]
 for j in range(3):
  lo,hi=sorted(rng.sample(range(-32768,32768),2));a,b=[rng.randrange(-32768,32768) for _ in range(2)]
  if i%11==0:b=a
  axes.append((a,b,lo,hi))
 cases.append(axes)
try:
 for axes in cases:
  lo,hi=Fraction(0),Fraction(1);valid=True
  for a,b,l,hb in axes:
   if a==b:
    if not l<=a<=hb:valid=False;break
   else:
    x,y=sorted([Fraction(l-a,b-a),Fraction(hb-a,b-a)]);lo=max(lo,x);hi=min(hi,y)
  valid=valid and lo<=hi
  write(0x31000,struct.pack('>12h',*[x for axis in axes for x in axis]));reg(17,0x2000)
  for k in range(1,17):reg(k,k*0x10101)
  reg(1,0x31000);reg(8,0x4fff0);pack(0x4fff0,'I',0x20000);saved=[reg(k) for k in range(1,17)]
  ok(u.uc_emu_start(h,0x10000,0x20000,1000000,2000))
  assert reg(9)==int(valid),(axes,reg(9),valid)
  if valid:assert Fraction(reg(10),reg(11))==lo
  assert reg(8)==0x4fff4
  assert all(reg(k)==saved[k-1] for k in range(1,17) if k not in (8,9,10,11))
 result=dict(passed=True,cases=len(cases),scope='Actual 68000 segment-box primitive compared with exact rational slab intersection. Signed-word coordinates, unsigned cross-products, exact entry fraction, preserved registers and stack.')
 Path('tmp/sweep-box-check.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
