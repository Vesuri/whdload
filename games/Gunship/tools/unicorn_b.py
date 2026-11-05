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
base=0x10000
u=C.CDLL(os.environ['AMIGA_UNICORN']+'/lib/libunicorn.2.dylib')
u.uc_open.argtypes=[C.c_int,C.c_int,C.POINTER(C.c_void_p)];u.uc_ctl.argtypes=[C.c_void_p,C.c_int]
u.uc_mem_map.argtypes=[C.c_void_p,C.c_uint64,C.c_size_t,C.c_uint32]
u.uc_mem_write.argtypes=[C.c_void_p,C.c_uint64,C.c_char_p,C.c_size_t];u.uc_mem_read.argtypes=[C.c_void_p,C.c_uint64,C.c_void_p,C.c_size_t]
u.uc_reg_write.argtypes=[C.c_void_p,C.c_int,C.c_void_p];u.uc_reg_read.argtypes=[C.c_void_p,C.c_int,C.c_void_p]
u.uc_emu_start.argtypes=[C.c_void_p,C.c_uint64,C.c_uint64,C.c_uint64,C.c_size_t];u.uc_close.argtypes=[C.c_void_p]
def ok(e):assert e==0,e

class CPU:
 def __init__(self):
  self.h=C.c_void_p();ok(u.uc_open(7,1<<30,C.byref(self.h)));ok(u.uc_ctl(self.h,7|(1<<26)|(1<<30),C.c_int(2)))
  ok(u.uc_mem_map(self.h,0,0x1000000,7));self.put(base,blob);self.rw(17,0x2000);self.rw(8,0x8f000)
 def put(self,a,b):ok(u.uc_mem_write(self.h,a,bytes(b),len(b)))
 def get(self,a,n):
  b=C.create_string_buffer(n);ok(u.uc_mem_read(self.h,a,b,n));return b.raw
 def rw(self,r,v):
  x=C.c_uint32(v);ok(u.uc_reg_write(self.h,r,C.byref(x)))
 def rr(self,r):
  x=C.c_uint32();ok(u.uc_reg_read(self.h,r,C.byref(x)));return x.value
 def call(self,entry,end=0x90000):
  self.put(self.rr(8),struct.pack('>I',0x90000));ok(u.uc_emu_start(self.h,entry,end,0,2000000))
 def close(self):ok(u.uc_close(self.h))
