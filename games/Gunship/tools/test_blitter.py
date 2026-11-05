#!/usr/bin/env python3
"""Execute assembled dispatcher and waits against original relocated PAL/NTSC code."""
from unicorn_b import *
from amitools.binfmt.Relocate import Relocate
root=Path(__file__).resolve().parents[1]
versions={'658':'Gunship','1489':'GunshipNTSC'}
cases=0
for version,folder in versions.items():
 img=BinFmt().load_image(str(root/'tmp/game'/folder/'data/gamemule'))
 addrs=[0x200000+i*0x20000 for i in range(len(img.get_segments()))]
 original=bytes(Relocate(img).relocate(addrs)[0]);gb=addrs[0]
 loops=[i for i in range(0,len(original)-8,2) if original[i:i+2] in [bytes.fromhex(x) for x in ('0828','0829','082e')] and original[i+2:i+8]==bytes.fromhex('0006000266f8')]
 pixel=next(i for i in range(0x8200,0x8300,2) if original[i:i+6]==bytes.fromhex('48e73ec04eb9') and original[i+16:i+22]==bytes.fromhex('2051d1c50706'))
 for kind in ['off','valid','german-dispatch','menu-dispatch','missing','extra','wrong-register','bad-pixel','duplicate-pixel','short','long']:
  c=CPU();c.put(base+symbol('_custom1'),struct.pack('>I',1));game=bytearray(original);size=len(game)+8
  if kind=='missing':game[loops[0]]=0
  if kind=='extra':game[0x9400:0x9408]=original[loops[0]:loops[0]+8]
  if kind=='wrong-register':game[loops[0]+1]=0x29
  if kind=='bad-pixel':game[pixel+20]=0
  if kind=='duplicate-pixel':
   game[0x9400:0x9416]=original[pixel:pixel+22];game[0x9406:0x940a]=struct.pack('>I',gb+0x942c)
  if kind=='short':size=0x9400
  if kind=='long':size=0x2000a
  if kind=='off':c.put(base+symbol('_custom1'),bytes(4))
  c.put(gb,game);c.put(gb-8,struct.pack('>I',size))
  expected={r:0x54320000+r*0x101 for r in range(1,17) if r!=8}
  expected[1]=base+symbol('pl_scrnmule_658' if kind=='menu-dispatch' else 'pl_gamemule_'+('german' if kind=='german-dispatch' else version));expected[2]=gb
  for r,v in expected.items():c.rw(r,v)
  valid=kind in ('off','valid','german-dispatch','menu-dispatch')
  c.call(base+symbol('blitter_dispatch'),0x90000 if valid else base+symbol('wrong_version'))
  after=c.get(gb,len(game))
  if valid:
   assert all(c.rr(r)==v for r,v in expected.items()),kind
   assert c.rr(8)==0x8f004
   want=bytearray(game)
   if kind not in ('off','menu-dispatch'):
    for off in loops:want[off:off+8]=b'\x4e\xb9'+struct.pack('>I',base+symbol('blitter_wait'))+b'\x4e\x71'
    want[pixel+6:pixel+10]=struct.pack('>I',base+symbol('blitter_pixel'))
    assert c.get(base+symbol('blitter_pixel_target'),4)==original[pixel+6:pixel+10]
   assert after==want,(kind,[(hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b][:32],hex(c.rr(18)))
  else:
   assert c.rr(18)==base+symbol('wrong_version'),(kind,hex(c.rr(18)))
   assert after==game,'partial patch on rejection'
  c.close();cases+=1
 print(version,'validated offsets',','.join(hex(x) for x in loops),'pixel',hex(pixel))
# Delayed BBUSY: first read is falsely clear, then busy, then clear.
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
for values in ([0,0],[0,0x40,0x40,0],[0x40,0x40,0]):
 for flags in range(32):
  c=CPU();c.rw(17,0x2000|flags);reads=[]
  expected={r:0x13570000+r*0x123 for r in range(1,17) if r!=8}
  for r,v in expected.items():c.rw(r,v)
  def read(h,access,address,size,value,user):
   v=values[min(len(reads),len(values)-1)];reads.append(v);c.put(address,bytes([v]))
  cb=CALLBACK(read);hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<10,cb,None,0xdff002,0xdff002))
  c.call(base+symbol('blitter_wait'))
  assert reads==list(values),reads
  assert all(c.rr(r)==v for r,v in expected.items())
  assert c.rr(8)==0x8f004
  c.put(0x90000,bytes.fromhex('40c04e71'));ok(u.uc_emu_start(c.h,0x90000,0x90002,0,10))
  assert c.rr(9)&31==flags|4,(flags,c.rr(9))
  c.close();cases+=1
print(cases,'assembled dispatch/negative/CCR/delayed-busy cases passed')
# Run the actual displaced coordinate helper, including its real register/CCR result.
for version,folder in versions.items():
 img=BinFmt().load_image(str(root/'tmp/game'/folder/'data/gamemule'))
 addrs=[0x200000+i*0x20000 for i in range(len(img.get_segments()))];data=Relocate(img).relocate(addrs)
 pixel=next(i for i in range(0x8200,0x8300,2) if data[0][i:i+6]==bytes.fromhex('48e73ec04eb9') and data[0][i+16:i+22]==bytes.fromhex('2051d1c50706'))
 helper=int.from_bytes(data[0][pixel+6:pixel+10],'big');bitmap_ptr=int.from_bytes(data[0][helper-addrs[0]+2:helper-addrs[0]+6],'big')
 for flags in range(32):
  results=[]
  for patched in (False,True):
   c=CPU()
   for addr,b in zip(addrs,data):c.put(addr,b)
   c.put(bitmap_ptr,struct.pack('>I',0x400000));c.put(0x400000,struct.pack('>HHBBH5I',40,200,0,5,0,*[0x500000+i*0x10000 for i in range(5)]))
   c.put(base+symbol('blitter_pixel_target'),struct.pack('>I',helper))
   for r in range(1,17):
    if r!=8:c.rw(r,0x12340000+r)
   c.rw(9,17);c.rw(10,12);c.rw(17,0x2000|flags)
   c.call(base+symbol('blitter_pixel') if patched else helper)
   registers=[c.rr(r) for r in range(1,17)]
   c.put(0x90000,bytes.fromhex('40c04e71'));ok(u.uc_emu_start(c.h,0x90000,0x90002,0,10))
   results.append((registers,c.rr(9)&31));c.close()
  assert results[0]==results[1],(version,flags,results)
  cases+=1
print(cases,'total cases including actual PAL/NTSC pixel-helper equivalence passed')
# BltClear wrapper: all supplied modules, gate, flag preservation and stack ABI.
for version,folder in versions.items():
 for module in ('titlmule','scrnmule','gamemule'):
  img=BinFmt().load_image(str(root/'tmp/game'/folder/'data'/module))
  data=bytes(img.get_segments()[0].get_data()); sig=bytes.fromhex('4cef0003000c4eaefed42c5f4e75')
  assert data.count(sig)==1,(version,module)
  off=data.index(sig);gb=0x200000
  for enabled in (0,1):
   c=CPU();c.put(gb,data);c.put(gb-8,struct.pack('>I',len(data)+8));c.put(base+symbol('_custom1'),struct.pack('>I',enabled));c.rw(2,gb)
   c.call(base+symbol('blitter_clear_dispatch'))
   wanted=bytearray(data)
   if enabled:wanted[off+6:off+12]=b'\x4e\xf9'+struct.pack('>I',base+symbol('blitter_clear_wait'))
   assert c.get(gb,len(data))==wanted
   if enabled:
    for flags in (0,1,2,4,6,0x12340006):
     c.close();c=CPU();c.put(gb,wanted)
     sp=0x8f000;c.rw(8,sp);c.rw(7,0x80000)
     # Enter after wrapper saved a6: saved a6, caller return, pointer, size, flags.
     c.put(sp,struct.pack('>5I',0x765432,0x90000,0x400000,6000,flags));c.put(0x80000-300,b'\x4e\x75')
     ok(u.uc_emu_start(c.h,gb+off,0x80000-300,0,100))
     assert c.rr(9)==6000 and c.rr(10)==flags|1
     ok(u.uc_emu_start(c.h,0x80000-300,0x90000,0,100))
     assert c.rr(7)==0x765432 and c.rr(8)==sp+8,(version,module,flags,hex(c.rr(7)),hex(c.rr(8)),hex(c.rr(18)))
   c.close()
print('PAL/NTSC title, menu and game BltClear wrappers passed; WAIT preserves all other flags')
