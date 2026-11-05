import ctypes as C,json,os,random,re,struct
from pathlib import Path
u=C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.dylib'))
P=C.c_void_p; U=C.c_uint64; Z=C.c_size_t; I=C.c_int
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
def trunc(x):return abs(x)//65536*(-1 if x<0 else 1)

sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',Path('tmp/traffic-slot-micro.lst').read_text(),re.M)}
write(0x10000,Path('tmp/traffic-slot-micro.bin').read_bytes())
sp=0x4fff0;stop=0x20000;a4=0x30000;a5=0x48000;record=0x50000;actor=0x38000;table=0x60000;comp=0x390000
# Actual MOVE SR materializes Unicorn lazy flags before reading them.
write(stop,bytes.fromhex('40f9000210004e71'));end=stop+8
rng=random.Random(612);bounds=0;pairs=0
for count in [0,1,12,65535]:
 for size in [0,count*16,max(0,count*16-16)]:
  for ptr in [table-2,table,table+1,table+45,table+46,table+max(count-1,0)*46,table+count*46-1,table+count*46,0xfffffffe]:
   for allocated in [0,comp]:
    pack(a4+0xaf04-65536,'HI',count,table);pack(sy['_traffic_memory'],'II',allocated,size)
    reg(17,0x2000);reg(1,ptr);reg(2,0xabcdef);reg(5,a4);reg(8,sp);reg(9,0x12345678);reg(10,0x87654321);pack(sp,'I',stop)
    before=[reg(k) for k in range(1,17)]
    ok(u.uc_emu_start(h,sy['_traffic_slot'],end,1000000,1000))
    d=ptr-table;valid=allocated and 0<=d<count*46 and d%46==0 and d//46*16<size
    assert reg(2)==(comp+d//46*16 if valid else 0),(count,size,ptr,allocated,hex(reg(2)))
    assert all(reg(k)==before[k-1] for k in range(1,17) if k not in (2,8));assert reg(8)==sp+4;bounds+=1
from game_image import hunks
native=hunks()[0]['data']
for i,(name,start,length) in enumerate([('speed',0xce8a,42),('phase',0xd36e,18),('collision',0xbc4c,6)]):
 original=0x18000+i*0x100
 write(original,native[start:start+length]+b'\x4e\x75')
 for speed in range(256):
  for target,accel in [(0,1),(20,2),(127,3),(128,255),(255,127)]:
   initial=[rng.randrange(2**32) for _ in range(16)]
   initial[0]=record;initial[4]=a4;initial[5]=a5;initial[7]=sp
   states=[]
   for entry in [original,sy['_traffic_'+name]]:
    pack(a4+0xaf04-65536,'HI',12,table);pack(sy['_traffic_memory'],'II',comp,192)
    write(record,bytes([0xa5])*46);pack(record+21,'BBB',accel,target,speed);write(actor,bytes([0x5a])*44)
    pack(a5+8,'I',record);pack(a5-8,'I',actor)
    reg(17,0x2000|(speed&31))
    for k,v in enumerate(initial,1):reg(k,v)
    pack(sp,'I',stop);ok(u.uc_emu_start(h,entry,end,1000000,1000))
    states.append(([reg(k) for k in range(1,17)],read(record,46),read(actor,44),read(0x21000,2)))
   assert states[0]==states[1],(name,speed,target,accel,states)
   pairs+=1
result=dict(passed=True,slot_boundary_cases=bounds,native_fallback_pairs=pairs,registers_stack_memory_and_CCR=True)
Path('tmp/traffic-slot-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
ok(u.uc_close(h))
