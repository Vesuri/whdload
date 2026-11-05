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
object_address=117524;copy_address=0x45000;vertices_address=0x50000
obj=read(object_address,56);write(copy_address,obj);pack(a4+0xe936-65536,'I',vertices_address)
reg(8,sp);pack(sp,'I',stop);pack(sp+4,'I',copy_address)
ok(u.uc_emu_start(h,code+0x97dc,stop,1000000,1000000));assert reg(18)==stop
nv=struct.unpack_from('>H',obj,20)[0];nn=obj[22];nf=obj[23]
verts=[list(struct.unpack('>3h',read(vertices_address+i*6,6))) for i in range(nv+nn)]
ptr=struct.unpack_from('>I',obj,52)[0];faces=[]
for i in range(nf):
 n,normal=read(ptr,2);indices=list(read(ptr+2,n));color=read(ptr+2+n,1)[0];ptr+=n+3
 faces.append(dict(index=i,indices=indices,normal_index=normal,normal=verts[normal],vertices=[verts[j] for j in indices],color=color))
observed=json.loads(Path('tmp/prof/c4-jump-surface-raw/collision-objects.json').read_text());observed=[r for r in observed if r['field']==135 and r['site']==0x9b2e and r['vertex_count']>=3]
matched=[]
for r in observed:
 polygon=[[r['plane_'+str(i+j)] for j in range(3)] for i in range(0,r['vertex_count']*3,3)]
 matched.append([f['index'] for f in faces if f['vertices']==polygon])
report=dict(scope='Native geometry transform of a cloned object into private scratch using saved render inputs; checks geometry correspondence only, not physics-pose update or runtime integration.',vertices=nv,normals=nn,faces=faces,observed_matches=matched,passed=all(len(m)==1 for m in matched))
Path('tmp/c4-object-mesh-check.json').write_text(json.dumps(report,indent=2)+'\n');print('Counts',nv,nn,nf,'matches',matched,'passed',report['passed']);ok(u.uc_close(h))
