#!/usr/bin/env python3
"""Execute the assembled frame hook: register/CCR preservation, edge and overflow cases."""
import ctypes as C,os,re,struct
from pathlib import Path
import _amigaxdev
from amitools.binfmt.BinFmt import BinFmt
root=Path(__file__).resolve().parents[1];build=root/'tmp/build'
blob=bytes(BinFmt().load_image(str(build/'verify/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'verify/Gunship.lst').read_text(encoding='latin1')
symbol=lambda name:int(re.search(r'^([0-9A-F]{8}) '+name+r'$',listing,re.M)[1],16)
base=0x10000;entry=base+symbol('verify_frame');mark=base+symbol('verify_marker');log=base+symbol('verify_frames');cap=8192
u=C.CDLL(os.environ['AMIGA_UNICORN']+'/lib/libunicorn.2.dylib')
u.uc_open.argtypes=[C.c_int,C.c_int,C.POINTER(C.c_void_p)];u.uc_ctl.argtypes=[C.c_void_p,C.c_int]
u.uc_mem_map.argtypes=[C.c_void_p,C.c_uint64,C.c_size_t,C.c_uint32]
u.uc_mem_write.argtypes=[C.c_void_p,C.c_uint64,C.c_char_p,C.c_size_t];u.uc_mem_read.argtypes=[C.c_void_p,C.c_uint64,C.c_void_p,C.c_size_t]
u.uc_reg_write.argtypes=[C.c_void_p,C.c_int,C.c_void_p];u.uc_reg_read.argtypes=[C.c_void_p,C.c_int,C.c_void_p]
u.uc_emu_start.argtypes=[C.c_void_p,C.c_uint64,C.c_uint64,C.c_uint64,C.c_size_t];u.uc_close.argtypes=[C.c_void_p]
def ok(e):assert e==0,e
cases=0
for count in (0,cap-1,cap,cap+1):
 for flags in range(32):
  h=C.c_void_p();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,7|(1<<26)|(1<<30),C.c_int(2)));ok(u.uc_mem_map(h,base,0x90000,7))
  def put(a,b):ok(u.uc_mem_write(h,a,b,len(b)))
  def get(a,n):b=C.create_string_buffer(n);ok(u.uc_mem_read(h,a,b,n));return b.raw
  def rw(r,v):x=C.c_uint32(v);ok(u.uc_reg_write(h,r,C.byref(x)))
  def rr(r):x=C.c_uint32();ok(u.uc_reg_read(h,r,C.byref(x)));return x.value
  put(base,blob);put(mark+8,struct.pack('>I',0x30000));put(mark+16,struct.pack('>I',0x50000));put(mark+32,struct.pack('>I',0x60000));put(mark+44,struct.pack('>III',count,123,0));put(mark+60,struct.pack('>I',log));put(0x5001c,struct.pack('>I',456));put(0x63b94,struct.pack('>H',789));put(0x64bb0,struct.pack('>H',1));put(0x3c757,b'\xff');put(log+cap*8,b'guard'*8)
  expected={r:0x13570000+r*0x123 for r in range(1,17) if r!=8}
  rw(17,0x2000|flags)
  for r,v in expected.items():rw(r,v)
  rw(8,0x8f000);put(0x8f000,struct.pack('>I',0x90000))
  if count<cap:
   checkpoint=base+symbol('verify_frame_tick')
   ok(u.uc_emu_start(h,entry,checkpoint,0,1000))
   assert rr(9)==(1<<16)|789,'CPU buffer/tick checkpoint'
   ok(u.uc_emu_start(h,checkpoint,0x90000,0,1000))
  else:ok(u.uc_emu_start(h,entry,0x90000,0,1000))
  assert all(rr(r)==v for r,v in expected.items())
  assert rr(8)==0x8f004
  # Unicorn exposes lazy flags via guest code; materialize SR into D0 first.
  put(0x90000,bytes.fromhex('40c04e71'));ok(u.uc_emu_start(h,0x90000,0x90002,0,10))
  assert rr(9)&31==(flags&16)|4,(flags,hex(rr(9)))
  assert get(0x3c757,1)==b'\0'
  assert get(log+cap*8,40)==b'guard'*8
  assert int.from_bytes(get(mark+44,4),'big')==count+(count<cap)
  assert int.from_bytes(get(mark+52,4),'big')==(count>=cap)
  if count<cap:assert get(log+count*8,8)==struct.pack('>IHH',456,789,1)
  ok(u.uc_close(h));cases+=1
print(f'{cases} frame-hook register/CCR/bounds cases passed')
