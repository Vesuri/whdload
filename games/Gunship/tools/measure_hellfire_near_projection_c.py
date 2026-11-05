"""Project recorded Hellfire forecast errors through native actor geometry."""
from unicorn_b import *
import json,sys
base=0x100000
listing=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
live=(build/'duration-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
reports=[]
for folder in map(Path,sys.argv[1:]):
 for m in json.loads((folder/'actor-forecast-dependency-audit.json').read_text())['mismatches']:
  directory=folder/f"world-{m['world']+1}";arena=(directory/'arena.bin').read_bytes();h=struct.unpack_from('>9I',arena,ls('RT_HUNKS'));rows=[]
  for distance in [64,96,128,192,256,384,512,768,1024,1536,2048,4096]:
   rows=[]
   for variant in ['predicted','native']:
    c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
    for i in [0,2,4,5,6]:c.put(h[i],(directory/f'h{i}.bin').read_bytes())
    ctx=h[6]+0x38f6;p=h[6]+0x3b88
    def call(entry,rs={},end=0x90000):
     for r,v in rs.items():c.rw(r,v)
     c.rw(8,0x8f000);c.call(entry,end);assert c.rr(18)==end
    for axis,value in enumerate(m['native' if variant=='control' else variant]):c.put(h[0]+0xc6a0+axis*12+2*m['slot'],bytes.fromhex(value))
    if variant=='control':
     address=h[0]+0xc6a0+2*m['slot'];c.put(address,struct.pack('>H',(int.from_bytes(c.get(address,2),'big')+256)&65535))
    call(h[0]+0x57e2,{6:p},h[0]+0x5830)
    call(base+sym('scene_state_build'),{1:h[4],2:h[0]+0xc6a0,3:h[6],4:ctx+14})
    # Synthetic camera looks along the native zero-heading axis. Keep the
    # two recorded projectile endpoints unchanged and move only the camera.
    nx,ny,nz=[int(x,16) for x in m['native']]
    c.put(ctx+14,struct.pack('>6H',nx,(ny-distance)&65535,nz,0,0,0))
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
   a,b=[r['visible'] for r in rows]
   correction=[b[0][k]-a[0][k] for k in ['x','y']] if a and b else None
   reports.append(dict(run=folder.name,world=m['world'],distance_coordinate_units=distance,projections=rows,correction_pixels=correction,visibility_changed=bool(a)!=bool(b)))
(root/'tmp/c/hellfire-near-projection-errors.json').write_text(json.dumps(reports,indent=2)+'\n')
for r in reports:print(r['run'],r['world'],r['distance_coordinate_units'],r['correction_pixels'],r['visibility_changed'])
