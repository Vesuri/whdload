"""Native rebuilt scene selection versus traversal-only vertex processing.
Drawing stubs are explicit; this is not a gameplay collision acceptance test.
"""
from unicorn_b import *
from layout import locate
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];ctx=h[6]+0x38f6;p=h[6]+0x3b88
module=bytes(BinFmt().load_image(str(root/'tmp/c/scene-state.hunk')).get_segments()[0].get_data())
stub=bytes(BinFmt().load_image(str(root/'tmp/c/skip-vertices.hunk')).get_segments()[0].get_data())
all_writes=set();capture_writes=False
cpus=[CPU(),CPU()];c=None;rows=[];current=None;special_calls=0;projectile_calls=0
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def observe(handle,a,n,user):
 global current,special_calls,projectile_calls
 off=a-h[0]
 if off==0x621c:special_calls+=1
 elif off==0x6224:projectile_calls+=1
 elif off==0x63dc:
  current=[c.rr(3),struct.unpack('>h',c.get(h[0]+0x6ac6,2))[0],c.get(ctx+0x50,6).hex()];rows.append(current)
 elif off==0x6818:current.extend([c.rr(2),c.get(c.rr(2),1)[0]])
 elif off==0x6922:current.extend([c.get(h[6]+0x3958,1)[0],c.get(h[0]+0x778a,current[4]).hex()])
WRITE=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
@WRITE
def observe_write(handle,kind,a,n,v,user):
 if capture_writes and not (0x8e000<=a<0x90000):all_writes.update(range(a,a+n))
hooks=[]
for cpu in cpus:
 hook=C.c_size_t();ok(u.uc_hook_add(cpu.h,C.byref(hook),1<<11,observe_write,None,1,0));hooks.append(hook)
 for off in [0x621c,0x6224,0x63dc,0x6818,0x6922]:
  hook=C.c_size_t();ok(u.uc_hook_add(cpu.h,C.byref(hook),1<<2,observe,None,h[0]+off,h[0]+off));hooks.append(hook)
def call(off,end=0x90000):
 c.rw(8,0x8f000);c.call(h[0]+off,end=end);assert c.rr(18)==end,(hex(off),hex(c.rr(18)))
odd=[]
trials=0;shape_visits=0;special_shapes=0;nonempty=0;positive=0;maxshapes=0
# Positions straddle 0x1000-cell rebasing boundaries and nearby coordinates.
for xy in [(0x7fff,0x7fff),(0x8000,0x8000),(0x8001,0x8001),(0x7800,0x8800)]:
 for height in [0,64,512]:
  for heading in range(0,256,32):
   results=[]
   for mode in range(2):
    capture_writes=False
    c=cpus[mode];c.put(0x200000,mem);c.put(base,module)
    c.put(h[0]+0x63f8,bytes.fromhex('4e75'));c.put(h[0]+0xa450,bytes.fromhex('4e75'));c.put(h[0]+0x6372,bytes.fromhex('6000ffe8'))
    if mode:c.put(h[0]+0x6642,stub)
    c.put(p,struct.pack('>HH',*xy));c.put(p+0x1c,struct.pack('>H',height));c.put(p+0x35,bytes([heading,0,0]));c.put(p+0x1a,b'\0')
    # Place the special object nearby, exercising its rotated-coordinate path.
    delta=0 if height==0 else 128
    special=struct.pack('>HHH',xy[0]+delta,xy[1]+delta,height+24)
    for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):c.put(h[6]+off,bytes([v]))
    c.put(h[6]+0x3ce3,bytes([(heading+64)&255]))
    coords=[xy[0]+(i-2)*128 for i in range(6)]+[xy[1]+(i-2)*128 for i in range(6)]+[height+32]*6
    c.put(h[0]+0xc6a0,struct.pack('>18H',*coords));c.put(h[0]+0xba08,b'\x00\x3f')
    c.rw(6,p);call(0x57e2,h[0]+0x5830)
    for r,v in {1:h[4],2:h[0]+0xc6a0,3:h[6],4:ctx+14,8:0x8f000}.items():c.rw(r,v)
    c.call(base);assert c.rr(9)==0
    c.put(ctx+0x5e,struct.pack('>I',h[6]+0x15dc));c.put(h[6]+0x3958,b'\0')
    capture_writes=bool(mode)
    c.rw(6,ctx);call(0x5c2e,h[0]+0x5c5c)
    rows=[];current=None;special_calls=0;projectile_calls=0
    call(0x60a8);call(0x6224)
    assert special_calls==1 and projectile_calls==1
    results.append((rows,c.get(h[6]+0x3958,1).hex()))
   assert results[0]==results[1],(xy,height,heading,results)
   odd.extend(dict(xy=xy,height=height,heading=heading,row=r) for r in rows if r[4]>20)
   trials+=1;shape_visits+=len(rows);maxshapes=max(maxshapes,len(rows));special_shapes+=sum(r[1]<0 for r in rows);nonempty+=sum(r[4]>0 for r in rows);positive+=results[1][1]!='00'
assert special_shapes>0 and nonempty>0
assert not odd, odd[:1]
ranges=[]
for a in sorted(all_writes):
 if ranges and a==ranges[-1][1]:ranges[-1][1]=a+1
 else:ranges.append([a,a+1])
report=dict(scratch_write_ranges=[[hex(a),hex(b)] for a,b in ranges],scenes=trials,shape_visits=shape_visits,special_shapes=special_shapes,nonempty_shapes=nonempty,positive_final_flags=positive,max_shapes=maxshapes,both_passes_per_scene=True)
(root/'tmp/c/scene-selection-odd.json').write_text(json.dumps(odd,indent=2)+'\n')
(root/'tmp/c/scene-selection-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
for cpu in cpus:cpu.close()
