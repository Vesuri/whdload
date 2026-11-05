import ctypes as C,json,os,random,re,struct,subprocess
from pathlib import Path
u=C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.dylib'))
P=C.c_void_p;U=C.c_uint64;Z=C.c_size_t;I=C.c_int
for name,args in [('uc_open',[I,I,C.POINTER(P)]),('uc_ctl',[P,C.c_uint32]),('uc_mem_map',[P,U,Z,C.c_uint32]),('uc_mem_write',[P,U,P,Z]),('uc_mem_read',[P,U,P,Z]),('uc_reg_write',[P,I,P]),('uc_reg_read',[P,I,P]),('uc_emu_start',[P,U,U,U,Z]),('uc_close',[P])]:
 f=getattr(u,name);f.argtypes=args;f.restype=I
u.uc_strerror.argtypes=[I];u.uc_strerror.restype=C.c_char_p
def ok(x):assert x==0,u.uc_strerror(x)
h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x10000,0x400000,7))
def write(a,b):ok(u.uc_mem_write(h,a,b,len(b)))
def read(a,n):b=C.create_string_buffer(n);ok(u.uc_mem_read(h,a,b,n));return b.raw
def reg(k,v=None):
 x=C.c_uint32(v or 0)
 if v is None:ok(u.uc_reg_read(h,k,C.byref(x)));return x.value
 ok(u.uc_reg_write(h,k,C.byref(x)))
def pack(a,fmt,*v):write(a,struct.pack('>'+fmt,*v))
root=Path('tmp');time=Path('src/HardDrivinTime.s').read_text();helper=time[time.index('_time_multiply_fields:'):time.index('; Q16 companion',time.index('_time_multiply_fields:'))]
syms=[]
for variant,path in enumerate([root/'traffic-p1-before.s',Path('src/HardDrivinTraffic.s')]):
 text=path.read_text();text=text[text.index('_traffic_slot:'):text.index('\tIFD VERIFY_TRAFFIC_MATH')]
 stem=root/f'p1-micro-{variant}';src=f' org ${0x10000+variant*0x10000:x}\n'+text+helper+'\n_time_scalar_fields: dc.w 8\n_traffic_memory: dc.l 0,0\n_traffic_extent: dc.l 0\n_traffic_valid: dc.l 0\n_traffic_fields: dc.w 8\n_traffic_factor: dc.w 128\n_traffic_hot: dc.w 0\n_traffic_world_return: dc.l 0\n_traffic_bias: dc.l 0\n'
 stem.with_suffix('.s').write_text(src);subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',stem.with_suffix('.lst').read_text(),re.M)};syms.append(sy);write(0x10000+variant*0x10000,stem.with_suffix('.bin').read_bytes())
sp=0x4fff0;stop=0x40000;record=0x50000;state=0x60000;a4=0x80000;rng=random.Random(768)
for off,val in [(0x98e0,0x100000),(0xaf26,0x101000),(0xaf0a,0x100c8),(0xaf0e,0x101f4),(0x9952,0x110000),(0xaf2a,0x110a0)]:pack(a4+off-65536,'I',val)
def call(v,name):
 reg(17,0x2000);reg(1,record);reg(2,state);reg(5,a4);reg(8,sp);pack(sp,'I',stop)
 ok(u.uc_emu_start(h,syms[v][name],stop,10000000,1000000));assert reg(8)==sp+4
cases=0
for i in range(24000):
 speed=rng.randint(-128,127);frac=rng.randint(-7,7);n=rng.choice([0,1,7,8,9,15,255,256,32768,65535,rng.randrange(256)]);accel=rng.randrange(4);target=rng.randrange(9,21)
 if i%2==0:speed=rng.choice([9,10,12,18,20,21]);frac=0
 last=speed if i%7 else speed+1;old=speed*8+frac;phase=rng.randrange(200);pc=rng.randrange(-127,128);micro=rng.randrange(-5,6)
 if i%2==0:pc=abs(pc);micro=abs(micro)
 if i%3==0:micro=0
 r=bytearray(46);struct.pack_into('>III',r,0,0x100000,0x100014,0x140000);struct.pack_into('>h',r,16,phase);r[20:24]=bytes([1,accel,target,speed&255]);r[19]=255
 st=struct.pack('>hhhhhBBhh',frac,last,old,pc,phase if i%11 else phase+1,0,int(i%17==0),micro,0)+bytes(30)
 results=[]
 for v in range(2):
  write(record,bytes(r));write(state,st);pack(syms[v]['_time_scalar_fields'],'H',n);pack(syms[v]['_traffic_fields'],'HHH',n,(16*n)&65535,0xffff if 9<=n<=255 else 0)
  if v and accel and i%3:
   cap=(target+accel-1)//accel*accel
   pack(state+14,'HBBBBBB',cap*8,accel,target,255,0,target,cap);pack(state+26,'HH',cap,cap*8);pack(state+30,'BBBB',1,accel,target,cap)
  # Test both isolated phase and complete speed+phase, retaining actual route bytes.
  if i%4:call(v,'_traffic_speed_step')
  call(v,'_traffic_phase_apply' if v else '_traffic_phase_step');results.append((read(record,46),read(state,14)))
 assert results[0]==results[1],(i,speed,frac,n,accel,target,pc,micro,results)
 cases+=1

# Persistent old/new companions exercise readiness, terminal-source changes and
# a changing field count, not merely freshly cleared state on every call.
hot=0
for trial in range(1000):
 accel=rng.randint(1,3);target=rng.randint(9,20);cap=(target+accel-1)//accel*accel
 r=bytearray(46);struct.pack_into('>III',r,0,0x100000,0x100014,0x140000);r[20:24]=bytes([1,accel,target,cap]);r[19]=255
 states=[bytes(46),bytes(46)];records=[bytes(r),bytes(r)]
 for step in range(20):
  n=rng.choice([1,7,8,9,13,15,255,256,0]);results=[]
  for v in range(2):
   write(record,records[v]);write(state,states[v]);pack(syms[v]['_time_scalar_fields'],'H',n);pack(syms[v]['_traffic_fields'],'HHH',n,(16*n)&65535,0xffff if 9<=n<=255 else 0)
   call(v,'_traffic_speed_step');hot+=v and bool(read(state+34,1)[0])
   call(v,'_traffic_phase_apply' if v else '_traffic_phase_step');records[v]=read(record,46);states[v]=read(state,46);results.append((records[v],states[v][:14]))
  assert results[0]==results[1],(trial,step,n,results)
  cases+=1
print('PASS',cases,'old/new complete traffic arithmetic and route pairs; hot',hot)
(root/'p1-micro.json').write_text(json.dumps(dict(passed=True,cases=cases,hot=hot,scope='Actual 68000 old/new speed/phase/route routines; all native record bytes and first 14 companion bytes'),indent=2)+'\n')
ok(u.uc_close(h))
