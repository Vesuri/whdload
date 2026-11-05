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

def words(b):return struct.unpack('>79H',b)
def signed(x):return x-65536 if x>=32768 else x
def blend(left,right,num,den):
 if num==den:return right
 result=[]
 for i,(x,y) in enumerate(zip(left,right)):
  kind=('uusaaap'[i] if i<7 else 'usuaaa'[(i-7)%6])
  if kind=='p':v=(((x&4095)*(den-num)+(y&4095)*num)//den)|(x&0xf000)
  elif kind=='a':
   x=signed(x);y=signed(y);d=y-x
   if d>720:d-=1440
   if d< -720:d+=1440
   v=x+d*num//den
   if v>720:v-=1440
   if v< -720:v+=1440
  else:
   if kind=='s':x=signed(x);y=signed(y)
   v=(x*(den-num)+y*num)//den
  result.append(v&65535)
 return tuple(result)

for addr,name in [(0x10000,'old'),(0x11000,'new')]:write(addr,Path('tmp/record-equal-'+name+'.bin').read_bytes())
rng=random.Random(3821);ret=0x18000;sp=0x4fff0;leftaddr=0x28000;rightaddr=0x29000;dest=0x2a000
cases=0;equal_words=0
try:
 for case in range(1280):
  den=rng.choice([1,2,8,9,16,31,255,32767,32768,65535,rng.randint(1,65535)])
  num=rng.choice([1,den,max(1,den//2),max(1,den-1),rng.randint(1,den)])
  left=[];right=[]
  for j in range(79):
   kind=('uusaaap'[j] if j<7 else 'usuaaa'[(j-7)%6])
   if kind=='a':x=rng.choice([-720,-719,-1,0,1,719,720,rng.randint(-720,720)])&65535;y=rng.randint(-720,720)&65535
   else:x=rng.choice([0,1,32767,32768,65535,rng.randrange(65536)]);y=rng.randrange(65536)
   if kind=='a' and case>=1200:x=rng.choice([-32768,-721,721,32767])&65535;y=x
   if case%3==0 or rng.random()<.5:y=x;equal_words+=1
   left.append(x);right.append(y)
  lb=struct.pack('>79H',*left);rb=struct.pack('>79H',*right);write(leftaddr,lb);write(rightaddr,rb)
  outputs=[]
  for code in [0x10000,0x11000]:
   reg(17,0x2010 if case%2 else 0x2000)
   for k in range(1,17):reg(k,k*0x10101)
   reg(1,leftaddr);reg(2,rightaddr);reg(3,dest);reg(11,num);reg(15,den);reg(8,sp);pack(sp,'I',ret)
   saved={k:reg(k) for k in [4,5,6,7,11,15,16]};write(dest-4,b'X'*166)
   ok(u.uc_emu_start(h,code,ret,1000000,30000));assert reg(18)==ret
   assert reg(8)==sp+4 and reg(3)==dest+158
   assert all(reg(k)==v for k,v in saved.items())
   assert read(dest-4,4)==read(dest+158,4)==b'XXXX'
   outputs.append(read(dest,158))
  expected=struct.pack('>79H',*blend(left,right,num,den))
  assert outputs[0]==outputs[1]==expected,(case,num,den)
  cases+=1
 result=dict(passed=True,assembled_68000_records=cases,words=cases*79,equal_input_words=equal_words,old_new_and_independent_model_exact=True,preserved_registers_and_stack=True,scope='Full records, signed/unsigned coordinates, angle seams, packed pitch/flags, full unsigned denominator range, equal and unequal endpoints.')
 Path('tmp/record-equal-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
