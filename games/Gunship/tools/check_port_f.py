from unicorn_b import *
from amitools.binfmt.Relocate import Relocate
from collections import deque
image=BinFmt().load_image(str(root/'tmp/game/GunshipNTSC/data/gamemule'))
h=[0x300000+i*0x10000 for i in range(9)]
c=CPU()
for addr,data in zip(h,Relocate(image).relocate(h)):c.put(addr,data)
blob=bytes(BinFmt().load_image(str(build/'release/GunshipNTSC.Slave')).get_segments()[0].get_data());c.put(base,blob)
listing=(build/'release/GunshipNTSC.lst').read_text(encoding='latin1')
syms={n:int(v,16) for v,n in re.findall(r'^([0-9A-F]{8}) (\w+)$',listing,re.M)}
ARENA=0x600000;TABLE=0x580000
c.put(TABLE,struct.pack('>9I',*h))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=deque(maxlen=25);entries={base+v:n for n,v in syms.items() if n.endswith('_prepare')}
@CODE
def watch(handle,addr,size,user):
 trace.append(addr-base)
 if addr in entries: print(entries[addr],flush=True)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,watch,None,1,0))
c.rw(1,ARENA);c.rw(2,TABLE);c.rw(9,60);c.call(base+syms['timing_runtime_prepare'])
print('result',hex(c.rr(9)),'ready',c.get(ARENA,4).hex(),'trace',[hex(n) for n in trace]);assert c.rr(9)==0
exe=0x510000;resload=0x520000
c.put(4,struct.pack('>I',exe))
c.put(exe-198,bytes.fromhex('203c007000004e75'))
c.put(resload+0x64,bytes.fromhex('70004e75'))
c.put(base+syms['_custom1'],struct.pack('>I',1))
for n in ['timing_live_install','timing_vbl_install','timing_render_install','timing_map_install','timing_gauges_install','timing_target_view_install','timing_actor_generation_install','timing_script_generation_install','timing_script_heading_install','timing_display_install','cpu_render_install','draw_overhead_install','cockpit_install','timing_loop_install']:
 c.put(ARENA+syms['RT_DRAW_READY'],b'\x00\x01')
 if n=='draw_overhead_install':c.put(h[0]+syms['GS0_8d7a'],b'\x4e\xb9'+struct.pack('>I',base+syms['blitter_wait'])+b'\x4e\x71')
 c.rw(1,ARENA);c.rw(3,resload);c.rw(8,0x8f000);c.call(base+syms[n])
 print(n,hex(c.rr(9)),flush=True)
 assert c.rr(9)==0,[hex(n) for n in trace]
c.close()
