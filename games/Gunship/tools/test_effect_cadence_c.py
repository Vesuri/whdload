"""Close the native slot-lifetime render cadence counterexample."""
from unicorn_b import *
from layout import locate
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);arena=0x300000;c.put(addr('timing_runtime_arena'),struct.pack('>I',arena));c.put(arena+addr('RT_HUNKS')-base,struct.pack('>9I',*h));c.put(arena+addr('RT_CAPTURE_OWNER')-base,b'\0\1')
results=[]
for render in (0,1,10):
 c.put(0x200000,mem);c.put(arena+addr('RT_HUNKS')-base,struct.pack('>9I',*h));c.put(arena+addr('RT_CAPTURE_OWNER')-base,b'\0\1');c.put(arena+addr('RT_BOUNDARY_PHASE')-base,bytes(2));c.put(h[0]+0xba08,b'\0\1');data=bytearray(90);data[0]=64;data[6]=9;data[84]=12;data[78]=2;c.put(h[0]+0xc6d0,data);phase=0;tick=0
 for field in range(1,101):
  c.rw(8,0x8f000);c.rw(9,1);c.call(addr('timing_vbl_effect_timers'))
  c.rw(8,0x8f000);c.rw(1,h[0]+0xc6d0);c.call(addr('field_effects_step'))
  if render and field%render==0:c.rw(8,0x8f000);c.call(addr('timing_render_animation'))
  phase+=3
  if phase>=50:
   phase-=50;tick+=1;c.rw(2,h[0]+0xc6d0);c.rw(14,0)
   ok(u.uc_emu_start(c.h,h[0]+0xc456,h[0]+0xc4d2,0,1000))
   if c.get(h[0]+0xba08,2)==bytes(2):break
 assert (field,tick)==(67,4),(render,field,tick)
 results.append(dict(render_period=render,release_field=field,release_tick=tick))
print(json.dumps(dict(status='passed',runs=results)));c.close()
