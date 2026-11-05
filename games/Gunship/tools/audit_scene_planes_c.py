"""Read shape selections from the captured native scene, with drawing omitted."""
from unicorn_b import *
from layout import locate
import json,os
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c=CPU();c.put(0x200000,mem)
# Shape vertex projection and plane classification remain native. Return before
# polygon rasterization; omit draw submission. Point-only models have no planes.
c.put(h[0]+0x63f8,bytes.fromhex('4e75'))
c.put(h[0]+0xa450,bytes.fromhex('4e75'))
c.put(h[0]+0x6372,bytes.fromhex('6000ffe8'))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
if os.environ.get('SKIP_VERTICES'):
 stub=bytes(BinFmt().load_image(str(root/'tmp/c/skip-vertices.hunk')).get_segments()[0].get_data())
 c.put(h[0]+0x6642,stub)
if os.environ.get('REBUILD_SCENE'):
 # Build native camera from current player, then the committed endpoint.
 c.rw(6,h[6]+0x3b88);c.rw(8,0x8f000);c.call(h[0]+0x57e2,end=h[0]+0x5830)
 c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scene-state.hunk')).get_segments()[0].get_data()))
 for r,v in {1:h[4],2:h[0]+0xc6a0,3:h[6],4:h[6]+0x3904,8:0x8f000}.items():c.rw(r,v)
 c.call(base);assert c.rr(9)==0
 ctx=h[6]+0x38f6
 c.put(ctx+0x5e,struct.pack('>I',h[6]+0x15dc));c.put(h[6]+0x3958,b'\0')
 c.rw(6,ctx);c.rw(8,0x8f000);c.call(h[0]+0x5c2e,end=h[0]+0x5c5c)
 assert c.rr(18)==h[0]+0x5c5c
rows=[];current=None
@CODE
def observe(handle,a,n,user):
 global current
 off=a-h[0]
 if off==0x63dc:
  ctx=c.rr(6);model=c.rr(3)
  current=dict(model=hex(model),object_index=struct.unpack('>h',c.get(h[0]+0x6ac6,2))[0],context=c.get(ctx+0x50,6).hex(),vertex_count=c.get(model,1)[0]+1)
  rows.append(current)
 elif off==0x6818:
  current['plane_header']=hex(c.rr(2));current['plane_count']=c.get(c.rr(2),1)[0]
 elif off==0x6922:
  current['flag']=c.get(h[6]+0x3958,1)[0]
  current['facing_bytes']=c.get(h[0]+0x778a,current['plane_count']).hex()
hooks=[]
for off in [0x63dc,0x6818,0x6922]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,observe,None,h[0]+off,h[0]+off));hooks.append(hook)
c.rw(6,h[6]+0x38f6);c.rw(8,0x8f000);c.call(h[0]+0x60a8)
assert c.rr(18)==0x90000
result=dict(shapes=rows,final_flag=c.get(h[6]+0x3958,1).hex())
path=root/('tmp/c/scene-planes-rebuilt.json' if os.environ.get('REBUILD_SCENE') else 'tmp/c/scene-planes-native.json')
if os.environ.get('SKIP_VERTICES'):
 assert result==json.loads(path.read_text())
 print('PASS: identical shape order, plane pointers, visibility bytes and final flag without vertex projection')
else:
 path.write_text(json.dumps(result,indent=2)+'\n')
 print(dict(shapes=len(rows),nonempty=sum(r['plane_count']>0 for r in rows),final_flag=result['final_flag']))
c.close()
