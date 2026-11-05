"""Native rebuilt scene selection versus traversal-only vertex processing.
Drawing stubs are explicit; this is not a gameplay collision acceptance test.
"""
from unicorn_b import *
from layout import locate
import json
image=BinFmt().load_image(str(root/"tmp/game/Gunship/data/gamemule"))
relocs=[r.offset for seg in image.get_segments()[0].get_reloc_to_segs() for r in image.get_segments()[0].get_reloc(seg).get_relocs()]
START=0x5a24;END=0x77b8;CLONE=0x400000;COORD=CLONE+0x1d94;CONTEXT=CLONE+0x1e4c
native_ctx=ctx if "ctx" in globals() else 0
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];ctx=h[6]+0x38f6;p=h[6]+0x3b88
native_ctx=ctx;flag=h[6]+0x3958
def normal(a):
 for lo,hi,orig in [(CLONE,CLONE+END-START,h[0]+START),(COORD,COORD+0xb8,h[6]+0x18dc),(CONTEXT,CONTEXT+0x64,native_ctx)]:
  if lo<=a<hi:return orig+a-lo
 return a
module=bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-world-scene.hunk')).get_segments()[0].get_data())
listing=(root/'tmp/c/scheduled-world-scene.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
stub=bytes(BinFmt().load_image(str(root/'tmp/c/skip-vertices.hunk')).get_segments()[0].get_data())
all_writes=set();capture_writes=False
cpus=[CPU(),CPU()];c=None;rows=[];current=None;special_calls=0;projectile_calls=0
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def observe(handle,a,n,user):
 global current,special_calls,projectile_calls
 off=normal(a)-h[0]
 if off==0x621c:special_calls+=1
 elif off==0x6224:projectile_calls+=1
 elif off==0x63dc:
  current=[normal(c.rr(3)),struct.unpack('>h',c.get(CLONE+0x6ac6-START if mode else h[0]+0x6ac6,2))[0],c.get(ctx+0x50,6).hex()];rows.append(current)
 elif off==0x6818:current.extend([normal(c.rr(2)),c.get(c.rr(2),1)[0]])
 elif off==0x6922:current.extend([c.get(flag,1)[0],c.get((CLONE+0x778a-START if mode else h[0]+0x778a),current[4]).hex()])
WRITE=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
@WRITE
def observe_write(handle,kind,a,n,v,user):
 if capture_writes and not (0x8e000<=a<0x90000):all_writes.update(range(a,a+n))
hooks=[]
for cpu in cpus:
 hook=C.c_size_t();ok(u.uc_hook_add(cpu.h,C.byref(hook),1<<11,observe_write,None,1,0));hooks.append(hook)
 for off in [0x621c,0x6224,0x63dc,0x6818,0x6922]:
  hook=C.c_size_t();ok(u.uc_hook_add(cpu.h,C.byref(hook),1<<2,observe,None,h[0]+off,h[0]+off));hooks.append(hook)
  hook=C.c_size_t();ok(u.uc_hook_add(cpu.h,C.byref(hook),1<<2,observe,None,CLONE+off-START,CLONE+off-START));hooks.append(hook)
def call(off,end=0x90000):
 c.rw(8,0x8f000);c.call((CLONE+off-START if mode and START<=off<END else h[0]+off),end=(CLONE+end-h[0]-START if mode and h[0]+START<=end<h[0]+END else end));assert normal(c.rr(18))==end,(hex(off),hex(c.rr(18)))
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
    ctx=native_ctx;flag=h[6]+0x3958
    if mode:
     ctx=CONTEXT;flag=CONTEXT+0x62
     for r,v in {1:h[0],2:h[6],3:CLONE,8:0x8f000}.items():c.rw(r,v)
     c.call(sym('scene_private_prepare'));assert c.rr(9)==0
    else:
     c.put(h[0]+0x63f8,bytes.fromhex('4e75'));c.put(h[0]+0xa450,bytes.fromhex('4e75'));c.put(h[0]+0x6372,bytes.fromhex('6000ffe8'))
    c.put(p,struct.pack('>HH',*xy));c.put(p+0x1c,struct.pack('>H',height));c.put(p+0x35,bytes([heading,0,0]));c.put(p+0x1a,b'\0');c.put(p+0x18,b'\x07')
    # Place the special object nearby, exercising its rotated-coordinate path.
    delta=0 if height==0 else 128
    special=struct.pack('>HHH',xy[0]+delta,xy[1]+delta,height+24)
    for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):c.put(h[6]+off,bytes([v]))
    c.put(h[6]+0x3ce3,bytes([(heading+64)&255]))
    coords=[xy[0]+(i-2)*128 for i in range(6)]+[xy[1]+(i-2)*128 for i in range(6)]+[height+32]*6
    c.put(h[0]+0xc6a0,struct.pack('>18H',*coords));c.put(h[0]+0xba08,b'\x00\x3f')
    c.rw(6,p);call(0x57e2,h[0]+0x5830)
    if mode:
     TS=0x500000;TC=0x501000;TH=0x502000;CQ=0x504000;SG=0x505000
     for name,args in [('clock_init',{1:TC,9:0,10:50}),('history_init',{1:TH,9:0}),('commands_init',{1:CQ,9:0}),('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})]:
      for r,v in args.items():c.rw(r,v)
      c.rw(8,0x8f000);c.call(sym(name));assert c.rr(9)==0
     c.put(TS+12,struct.pack('>HH',2,1));c.put(TS+24,struct.pack('>I',trials+1))
     c.put(SG,struct.pack('>IIII',TS,p,CLONE,h[0]+0xc6a0)+bytes(10))
    rows=[];current=None;special_calls=0;projectile_calls=0
    capture_writes=bool(mode)
    if mode:
     all_writes.clear();native_before=c.get(h[0],0xf0c8)+c.get(h[6],0x4600)
     for r,v in {1:SG,8:0x8f000}.items():c.rw(r,v)
     saved={r:c.rr(r) for r in range(1,17) if r not in [8,9]}
     c.call(sym('scheduled_world_scene'));assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
     assert all(c.rr(r)==v for r,v in saved.items())
     assert c.rr(9)==int(c.get(flag,1)!=b'\0')
     assert c.get(SG+16,10)==struct.pack('>IHHH',trials+1,1,1,int(c.get(flag,1)!=b'\0'))
     first_rows=list(rows);first_flag=c.get(flag,1)
     c.rw(8,0x8f000);c.call(sym('scheduled_world_scene'))
     assert c.rr(9)==0xfffffffd and rows==first_rows and c.get(flag,1)==first_flag
    else:
     for r,v in {1:h[4],2:h[0]+0xc6a0,3:h[6],4:ctx+14,8:0x8f000}.items():c.rw(r,v)
     c.call(sym('scene_state_build'));assert c.rr(9)==0
     c.put(ctx+0x5e,struct.pack('>I',h[6]+0x15dc));c.put(flag,b'\0')
     c.rw(6,ctx);call(0x5c2e,h[0]+0x5c5c)
     call(0x60a8);call(0x6224)
    assert special_calls==1 and projectile_calls==1
    if mode:
     expected=bytearray(native_before)
     expected[0xf0c8+0x3ba0]=1 if c.get(flag,1)!=b'\0' else 7
     assert bytes(expected)==c.get(h[0],0xf0c8)+c.get(h[6],0x4600),'unexpected native state change'
     assert all(CLONE<=a<CLONE+END-START or COORD<=a<COORD+0xb8 or CONTEXT<=a<CONTEXT+0x64 or a==p+0x18 or SG<=a<SG+26 for a in all_writes),[hex(a) for a in all_writes if not CLONE<=a<CONTEXT+0x64]
    results.append((rows,c.get(flag,1).hex()))
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
(root/'tmp/c/scheduled-world-scene-odd.json').write_text(json.dumps(odd,indent=2)+'\n')
(root/'tmp/c/scheduled-world-scene-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
# Fresh CPU ensures the post-check fault hook precedes translated execution.
old=c;c=CPU();c.put(0x200000,old.get(0x200000,0x800000));c.put(base,module)
capture_writes=False
c.put(SG+16,bytes(10))
for phase,due in [(0,1),(1,1),(2,0)]:
 c.put(TS+12,struct.pack('>HH',phase,due));c.rw(1,SG);c.rw(8,0x8f000);c.call(sym('scheduled_world_scene'));assert c.rr(9)==0xfffffffd
c.put(TS+12,struct.pack('>HH',2,1))
xy_now=struct.unpack('>HH',c.get(p,4));height_now=struct.unpack('>H',c.get(p+0x1c,2))[0]
for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],struct.pack('>HHH',*xy_now,height_now+24)):c.put(h[6]+off,bytes([v]))
c.put(p+0x18,b'\x07');checks=0
@CODE
def fault(handle,a,n,user):
 global checks
 checks+=1
 if checks==2:c.put(TH+6,b'\0\1')
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,sym('scheduler_check'),sym('scheduler_check')))
c.rw(1,SG);c.rw(8,0x8f000);c.call(sym('scheduled_world_scene'))
assert checks==2 and c.rr(9)==0xffffffff
assert c.get(p+0x18,1)==b'\1' and c.get(SG+20,6)==struct.pack('>HHH',1,1,1)
c.put(TH+6,bytes(2));c.put(TS+22,bytes(2));c.rw(8,0x8f000);c.call(sym('scheduled_world_scene'));assert c.rr(9)==0xfffffffd
assert c.get(p+0x18,1)==b'\1'
print(dict(phase_rejections=3,post_publication_fault=True,retry_rejected=True))
c.close()
for cpu in cpus:cpu.close()
# Every relocated pointer is validated before any destination write.
c=CPU();c.put(0x200000,mem);c.put(base,module)
guards=[int(line.split(',')[0].split('$')[1],16)+START for line in (root/'tmp/c/scene-relocs.txt').read_text().splitlines()]
guards += [0x63f8,0x6372,0x6642,0x6356,0x6358,0x5c5c,0x5c5e]
canary=bytes([0xa5])*0x1eb8
for off in guards:
 original=c.get(h[0]+off,1);c.put(h[0]+off,bytes([original[0]^1]));c.put(CLONE,canary)
 for r,v in {1:h[0],2:h[6],3:CLONE,8:0x8f000}.items():c.rw(r,v)
 c.call(sym('scene_private_prepare'));assert c.rr(9)==0xffffffff
 assert c.get(CLONE,len(canary))==canary
 c.put(h[0]+off,original)
print(dict(signature_rejections=len(guards),destination_unchanged=True,repeated_workspace_cases=96))
c.close()
