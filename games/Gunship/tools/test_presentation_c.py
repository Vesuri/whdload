#!/usr/bin/env python3
"""Differential native camera/instrument builder and separate pitch clamp."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;g=h[6]+0x157d;camera=h[4];table=h[4]+0x1c8
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/presentation.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/presentation.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
rng=random.Random(5736);count=0
WRITE=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
unaligned=[]
@WRITE
def watch(handle,kind,address,size,value,user):
 if size>1 and address&1:unaligned.append((address,size))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,watch,None,0x310000,0x310010))
# Alternate output addresses certify there are no baked-in game destinations.
G=0x310001;V=0x320000
for n in range(768):
 G=0x310000+(n&1)
 b=bytearray(rng.randbytes(86));b[0x36]=n>>8;b[0x3e]=n&255
 if n<512:struct.pack_into('>H',b,28,0 if n<256 else 1)
 gauges=rng.randbytes(16);vector=rng.randbytes(12)
 c.put(p,b);c.put(g,gauges);c.put(camera,vector);c.rw(8,0x8f000);c.rw(6,p);c.rw(17,0x2000)
 c.call(h[0]+0x56d8,end=h[0]+0x5830)
 assert c.rr(18)==h[0]+0x5830
 native_record=c.get(p,86);native_gauge=c.get(g,16);native_camera=c.get(camera,12)
 if b[28:30]==bytes(2) and b[62]&128:
  native_gauge=native_gauge[:15]+bytes(1)
 c.put(p,b);c.put(G-1,b'\xa6'+gauges+b'\x6a');c.put(V-2,b'\xab\xcd'+vector+b'\xdc\xba')
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:p,2:G,3:V,4:table})
 def call(name):
  for r,v in regs.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+sym(name))
  assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
  assert all(c.rr(r)==v for r,v in regs.items()),name
 call('player_pitch_clamp');assert c.get(p,86)==native_record
 call('presentation_build')
 assert c.get(p,86)==native_record
 assert c.get(G,16)==native_gauge,(n,c.get(G,16).hex(),native_gauge.hex())
 assert c.get(V,12)==native_camera,(n,c.get(V,12).hex(),native_camera.hex())
 assert c.get(G-1,1)==b'\xa6' and c.get(G+16,1)==b'\x6a'
 assert c.get(V-2,2)==b'\xab\xcd' and c.get(V+12,2)==b'\xdc\xba'
 # Extra renders must leave authoritative player state unchanged.
 if n%256==0:
  call('presentation_build');assert c.get(p,86)==native_record
  assert c.get(G,16)==native_gauge and c.get(V,12)==native_camera
 count+=1
assert not unaligned,unaligned[:1]
r=dict(both_buffer_alignments=True,no_unaligned_instrument_writes=True,native_comparisons=count,repeat_renders=3,scope='all vertical byte values at zero and positive height, plus random airborne records; grounded descent displays zero; original table; register preservation and output guards')
(root/'tmp/c/presentation-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
