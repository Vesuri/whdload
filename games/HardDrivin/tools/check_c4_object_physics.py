"""Replay recorded zero-contact terrain inputs against optimized and native code."""
from pathlib import Path
import ctypes as C,json,os,random,re,struct,subprocess,sys
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0x9b0000,7));ok(u.uc_mem_map(h,0x7800000,0x800000,7))
sys.path.insert(0,'tools')
from game_image import hunks
from machine_profiles import banks
root=Path('tmp/prof/c4-jump-bad-plane');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base'];stop=0x41000;sp=0x4f000
images=[(addr,(root/f'loss-{name}.bin').read_bytes()) for name,addr,size in banks(meta['configuration'])]
hs=hunks();native=bytearray(hs[0]['data']);bases=[r['base'] for r in lay['regions']]
for off,dest in hs[0]['relocs']:struct.pack_into('>I',native,off,struct.unpack_from('>I',native,off)[0]+bases[dest])
def invoke(addr,arg=None):
 reg(8,sp);pack(sp,'I',stop)
 if arg is not None:pack(sp+4,'h',arg)
 ok(u.uc_emu_start(h,addr,stop,1000000,1000000));assert reg(18)==stop and reg(8)==sp+4
for addr,body in images:write(addr,body)
write(code,bytes(native));ok(u.uc_ctl(h,0x4000000a));reg(17,0x2000);reg(5,a4)
for dst,src in [(0xe93a,0x9448),(0xe93c,0x944a),(0xe93e,0x944c),(0xe940,0x944e),(0xe942,0x9450),(0xe944,0x9452),(0x9944,0x994a),(0x9946,0x994c),(0x9948,0x994e)]:write(a4+dst-65536,read(a4+src-65536,2))
object_address=117524;copy_address=0x45000;vertices_address=0x50000
obj=bytearray(read(object_address,56))
for i in range(3):
 value=struct.unpack_from('>h',obj,8+i*2)[0]-struct.unpack('>h',read(a4+0x98f6-65536+i*2,2))[0];struct.pack_into('>H',obj,i*2,value&65535)
write(copy_address,bytes(obj));pack(a4+0xe936-65536,'I',vertices_address)
reg(8,sp);pack(sp,'I',stop);pack(sp+4,'I',copy_address)
ok(u.uc_emu_start(h,code+0x97dc,stop,1000000,1000000));assert reg(18)==stop
nv=struct.unpack_from('>H',obj,20)[0];nn=obj[22];nf=obj[23]
verts=[list(struct.unpack('>3h',read(vertices_address+i*6,6))) for i in range(nv+nn)]
ptr=struct.unpack_from('>I',obj,52)[0];faces=[]
for i in range(nf):
 n,normal=read(ptr,2);indices=list(read(ptr+2,n));color=read(ptr+2+n,1)[0];ptr+=n+3
 faces.append(dict(index=i,indices=indices,normal_index=normal,normal=verts[normal],vertices=[verts[j] for j in indices],color=color))
exec(Path('tools/check_c4_support_faces.py').read_text().split("faces=raw[")[0])
wheel_vertices=[struct.unpack('>3h',read(a4+0x8cac-65536+i*6,6)) for i in range(4)];wheels=[]
for wheel in wheel_vertices:
 candidates=[]
 for f in faces:
  if len(f['vertices'])<3:continue
  y=support(f['vertices'],wheel[0],wheel[2])
  if y is None:continue
  pack(a4+0xe94e-65536,'9h',*(v for vert in f['vertices'][:3] for v in vert))
  reg(8,sp);pack(sp,'I',stop);pack(sp+4,'3h',*wheel);ok(u.uc_emu_start(h,code+0xc6ec,stop,1000000,1000000));assert reg(18)==stop
  result=reg(9)&65535;result=result-65536 if result&32768 else result
  candidates.append(dict(face=f['index'],native_distance=result,rational_distance=str(wheel[1]-y),rounding_error=float(result-(wheel[1]-y))))
 wheels.append(dict(point=wheel,candidates=candidates))
report=dict(scope='Private cloned object transformed at the current predicted physics pose, followed by finite per-wheel support tests and native plane distance. No renderer eligibility flags or object-type exclusion. Single saved object; not whole runtime or contact response acceptance.',faces=faces,wheels=wheels)
Path('tmp/c4-object-physics-pose.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(wheels,indent=2));ok(u.uc_close(h))
