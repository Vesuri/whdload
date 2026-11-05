"""Project recorded Hellfire forecast errors through native actor geometry."""
from unicorn_b import *
import json,sys
base=0x100000
listing=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
reports=[]
for folder in map(Path,sys.argv[1:]):
 for frame in json.loads((folder/'frames.json').read_text()):
  directory=folder/f"frame-{frame['frame']:03d}";arena=(directory/'arena.bin').read_bytes();h=struct.unpack_from('>9I',arena,ls('RT_HUNKS'));rows=[]
  m={'slot':5}
  for variant in ['presentation','committed']:
   c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
   for i in [0,2,4,5,6]:c.put(h[i],(directory/f'h{i}.bin').read_bytes())
   ctx=h[6]+0x38f6;p=h[6]+0x3b88
   def call(entry,rs={},end=0x90000):
    for r,v in rs.items():c.rw(r,v)
    c.rw(8,0x8f000);c.call(entry,end);assert c.rr(18)==end
   scene=arena[ls('RT_PRESENT_SCENE'):ls('RT_PRESENT_SCENE')+54]
   # Repeat native cell selection from its original global camera, not the
   # already-rebased camera left by the completed draw.
   assert c.get(ctx+18,50)==scene[4:], 'non-position scene changed during drawing'
   c.put(ctx+14,scene)
   if variant=='committed':
    c.put(ctx+26,c.get(h[0]+0xc6a0,36))
   # Scripted object is irrelevant; avoid its installed heading callback.
   c.put(ctx+0x3e,bytes(2))
   call(h[0]+0x5c2e,{6:ctx},h[0]+0x5c5c)
   # Keep actor projection and clipping, omit the final pixel drawing call.
   c.put(h[0]+0x63b0,bytes.fromhex('4e714e714e71'))
   points=[];visible=[]
   @CODE
   def point(handle,a,n,user):
    descriptor=int.from_bytes(c.get(ctx+0x5a,4),'big')-h[0]
    assert descriptor==0x5ad2+6*m['slot'],hex(descriptor)
    points.append(dict(x=struct.unpack('>h',struct.pack('>H',c.rr(15)&65535))[0],y=struct.unpack('>h',struct.pack('>H',c.rr(16)&65535))[0],descriptor=descriptor))
   hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,point,None,h[0]+0x63a0,h[0]+0x63a0))
   @CODE
   def drawn(handle,a,n,user):visible.append(dict(points[-1]))
   drawhook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(drawhook),1<<2,drawn,None,h[0]+0x63b0,h[0]+0x63b0))
   call(h[0]+0x6224,{6:ctx})
   rows.append(dict(variant=variant,points=points,visible=visible));c.close()
  reports.append(dict(frame=frame,projections=rows))
(folder/'frame-projections.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
