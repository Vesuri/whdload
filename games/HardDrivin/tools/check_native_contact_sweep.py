import ctypes as C,json,os,random,re,struct
from pathlib import Path
u=C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.dylib'))
P=C.c_void_p; U=C.c_uint64; Z=C.c_size_t; I=C.c_int
for name,args in [('uc_open',[I,I,C.POINTER(P)]),('uc_ctl',[P,C.c_uint32]),('uc_mem_map',[P,U,Z,C.c_uint32]),('uc_mem_write',[P,U,P,Z]),('uc_mem_read',[P,U,P,Z]),('uc_reg_write',[P,I,P]),('uc_reg_read',[P,I,P]),('uc_emu_start',[P,U,U,U,Z]),('uc_close',[P])]:
 f=getattr(u,name);f.argtypes=args;f.restype=I
u.uc_strerror.argtypes=[I];u.uc_strerror.restype=C.c_char_p
def ok(x):assert x==0,u.uc_strerror(x)
h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x100000,0x400000,7))
def write(a,b):ok(u.uc_mem_write(h,a,b,len(b)))
def read(a,n):b=C.create_string_buffer(n);ok(u.uc_mem_read(h,a,b,n));return b.raw
def reg(k,v=None):
 x=C.c_uint32(v or 0)
 if v is None:ok(u.uc_reg_read(h,k,C.byref(x)));return x.value
 ok(u.uc_reg_write(h,k,C.byref(x)))
def pack(a,fmt,*v):write(a,struct.pack('>'+fmt,*v))
def trunc(x):return abs(x)//65536*(-1 if x<0 else 1)

import subprocess,sys
sys.path.insert(0,'tools')
from game_image import hunks
codebase=0x100000;database=0x200000;a4=database+0x7ffe;bases=[codebase,database,0x300000]
def g(off):return database+off-0x8002
for index,hu in enumerate(hunks()):
 b=bytearray(hu['data'])
 for off,dest in hu['relocs']:struct.pack_into('>I',b,off,struct.unpack_from('>I',b,off)[0]+bases[dest])
 write(bases[index],bytes(b))
# Isolate contact detection and native response from audio hardware.
write(a4-0x7fce,bytes.fromhex('4e75'));write(a4-0x7fe0,bytes.fromhex('4e75'))
obj=0x350000;pack(g(0xb190),'h',1);pack(g(0xaf38),'HI',0,obj)
write(g(0xe931),b'\x00');write(g(0xe960),b'\x00');pack(g(0xe93a),'4h',0,16384,0,16384)
write(obj,bytes(40));write(obj+25,b'\x01');write(obj+28,b'\x08');write(obj+34,b'\xff')
pack(g(0xaf04),'h',0)
def contact(depth,car_z,projection,mph):
 pack(obj,'3h',0,0,depth)
 write(g(0x9606),b'\x00');pack(g(0x9928),'h',400);pack(g(0x992c),'h',mph)
 pack(g(0x991e),'3h',0,0,projection);pack(g(0x98fc),'3i',0,0,car_z*8)
 reg(17,0x2000);reg(5,a4);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
 ok(u.uc_emu_start(h,codebase+0xbaee,0x490000,1000000,10000));assert reg(8)==0x4ffff4
 return dict(depth=depth,car_z=car_z,result=reg(9),crash=read(g(0x9606),1)[0],velocity=struct.unpack('>h',read(g(0x9928),2))[0],after_z=struct.unpack('>i',read(g(0x9904),4))[0])
try:
 # Native velocity400 gives a projected600 long-units/update =75 world units.
 # MPH112 gives a forward bound floor(112/3)+40=77. Object starts100 ahead.
 rows=[contact(d,100-d,600,112) for d in [100,77,76,25,3,2,0,-1,-50]]
 native=[contact(100,0,600,112),contact(25,75,600,112)]
 long=[contact(100,0,600,112),contact(-50,150,600,112)]
 assert not native[0]['crash'] and native[1]['crash']==25
 assert all(not r['crash'] for r in long)
 r=dict(passed=True,scope='Actual pristine object-contact routine with private scene-space object coordinates and sound stubs. Constant velocity/heading synthetic movement, not a captured live route or integrated full solver.',velocity=400,mph=112,projection_long=600,object_distance_world=100,bounds_scan=rows,eight_field_movement_world=75,sixteen_field_movement_world=150,eight_field_contact=native,sixteen_field_miss=long,conclusion='Endpoint object collision eligibility can miss an object crossed by a two-native-step displacement. Long-frame handling needs swept contact or equivalent coverage; arithmetic scaling alone does not prove contact safety.')
 Path('tmp/native-contact-sweep.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
finally:ok(u.uc_close(h))
