"""Actual render hooks: capture, panel borrowing, hidden stale targets, restore."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();c.put(base,blob);c.put(0x200000,mem);arena=0x180000;table=0x170000;resload=0x740000;native=h[0]+0xa99e;scene=h[6]+0x38f6;model=0x160000;rng=random.Random(841)
def rt(n):return arena+sym('RT_'+n)
def call(entry,args={},want=None,keep=False):
 regs={r:rng.randrange(0x1000000) for r in list(range(1,8))+list(range(9,17))};regs.update(args);c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry);assert c.rr(18)==0x90000
 if want is not None:assert c.rr(9)==want,(hex(entry),c.rr(9),want)
 if keep:assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 return c.rr(9)
c.put(table,struct.pack('>9I',*h));call(addr('timing_runtime_prepare'),{1:arena,2:table,9:50},0,True)
c.put(addr('timing_runtime_arena'),struct.pack('>I',arena));c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'))
for enabled in (0,1):
 c.put(addr('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8))
 call(addr('timing_target_view_install'),{1:arena,3:resload},0,True)
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));assert image==h[0]
  for i,(off,name) in enumerate(((0x5c78,'timing_view_panel'),(0x46a4,'timing_view_draw'))):
   command,site,rel=struct.unpack('>HHh',c.get(patch+6*i,6));assert (command,site,patch+rel)==(0x8003,off,addr(name))
 else:assert c.get(0x750000,8)==bytes(8)
rejects=0
for off in (0x5c78,0x5c7a,0x5c7c,0x46a4,0x46a6,0x46a8):
 saved=c.get(h[0]+off,2);c.put(h[0]+off,bytes(v^1 for v in saved));before=c.get(addr('timing_view_native_panel'),8)
 call(addr('timing_target_view_install'),{1:arena,3:resload},0xffffffff,True)
 assert c.get(addr('timing_view_native_panel'),8)==before;c.put(h[0]+off,saved);rejects+=1
# Apply actual hooks; full selector ownership is the existing render guard.
c.put(addr('timing_render_native_select'),struct.pack('>I',h[0]+0xa58c));c.put(addr('timing_render_native_collect'),struct.pack('>I',h[0]+0xa450))
for off,name in ((0x468c,'timing_render_select'),(0x46a4,'timing_view_draw')):c.put(h[0]+off,bytes.fromhex('4eb9')+struct.pack('>I',addr(name)))
for off in (0xa6e4,0x44dc,0xa58c):c.put(h[0]+off,bytes.fromhex('4e75'))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
draws=[];scribble=False
@CODE
def drawn(handle,a,n,user):
 draws.append(c.get(native,168))
 if scribble:c.put(native,b'\x5a'*168)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,drawn,None,h[0]+0xa6e4,h[0]+0xa6e4))
c.put(model,struct.pack('>3H',0,0,64));c.put(scene+0x5a,struct.pack('>II',model,h[6]+0x15dc));c.put(h[4]+0x430,struct.pack('>HH',320,200));c.put(h[0]+0xa998,struct.pack('>3H',68,252,1000));c.put(h[6]+0x1d72,bytes(2));c.put(h[6]+0x3ba2,bytes(1));c.put(h[4]+0x1c5,bytes(1))
data=bytearray(c.get(native,168));data[0]=2;struct.pack_into('>HHH',data,2,0,7,3)
for i,off in enumerate((36,18,0,54,72)):struct.pack_into('>H',data,8+2*i,off)
cases=0
for visible in (False,True):
 for x in (20,80,160,300):
  for damage in (False,True):
   c.put(native,data);c.put(rt('CAPTURE_OWNER'),b'\0\1');c.put(rt('BOUNDARY_PHASE'),bytes(2));c.put(rt('TARGET_PHASE'),b'\0\2')
   call(addr('target_view_reset'),{1:rt('VIEW'),2:native},0,True);c.put(rt('VIEW_PHASE'),b'\0\1')
   descriptor=rng.randbytes(18);c.put(scene+0x44,descriptor)
   for off,value in ((0x6ac6,7 if visible else 9),(0x5b00,3),(0x6ac8,8),(0x76e2,x),(0x770c,100),(0x768e,1000)):c.put(h[0]+off,struct.pack('>H',value))
   before=c.get(native,168);call(addr('timing_render_collect'),{6:scene},keep=True);assert c.get(native,168)==before
   draws.clear();scribble=damage
   call(addr('timing_view_panel'),{6:scene},keep=True)
   assert c.get(native,168)==before and c.get(rt('VIEW_PHASE'),2)==bytes(2)
   assert len(draws)==int(visible),(visible,x,damage,len(draws))
   if visible:
    assert draws[0][:2]==data[:2] and draws[0][4:8]==data[4:8]
    assert draws[0][18:36]==descriptor and draws[0][0x80:0x82]==struct.pack('>H',x)
   # A second panel call cannot reuse the closed frame's view.
   calls_before=len(draws);call(addr('timing_view_panel'),{6:scene},keep=True);assert len(draws)==calls_before and c.get(native,168)==before
   cases+=1
# Commands and fire clear selection when exiting the map. Until the world
# reacquires, rendering must not run the native automatic map fallback.
c.put(h[0]+0x46de,bytes.fromhex('4e75'));fallbacks=[]
@CODE
def fallback(handle,a,n,user):fallbacks.append(1)
fallback_hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(fallback_hook),1<<2,fallback,None,h[0]+0x46de,h[0]+0x46de))
for status in (0x80,0xff):
 pending=bytearray(data);pending[0]=status;c.put(native,pending)
 c.put(h[4]+0x1c5,b'\0');c.put(rt('VIEW_PHASE'),b'\0\1')
 c.put(rt('VIEW')+sym('TPV_VALID'),b'\0\0');draws.clear()
 call(addr('timing_view_panel'),{6:scene},keep=True)
 assert not fallbacks and not draws
 assert c.get(native,168)==pending and c.get(h[4]+0x1c5,1)==b'\0'
 assert c.get(rt('VIEW_PHASE'),2)==bytes(2)
# Without enhanced ownership, the panel still calls the native painter.
scribble=False;c.put(rt('CAPTURE_OWNER'),bytes(2));c.put(native,data);draws.clear();call(addr('timing_view_panel'),{6:scene});assert len(draws)==1
print(json.dumps(dict(status='passed',panel_cases=cases,native_passthrough=True,stale_frame_hidden=True,adversarial_draw_restored=True,installer_rejections=rejects)));c.close()
