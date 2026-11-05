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
outputs={}
try:
 for name,pristine,entry in [('optimized_road',False,0xc854),('native_road',True,0xc854),('native_no_road',True,0xc94e),('native_object_surface',True,0xca14)]:
  for addr,body in images:write(addr,body)
  if pristine:write(code,bytes(native))
  ok(u.uc_ctl(h,0x4000000a));reg(17,0x2000);reg(5,a4)
  invoke(code+entry)
  wheel=struct.unpack('>4h',read(a4+0x947e-65536,8));outputs[name]=wheel
 raw_polys=json.loads(Path('tmp/prof/c4-jump-surface-raw/collision-objects.json').read_text())
 raw_polys=[r for r in raw_polys if r['field']==135 and r['site']==0x9b2e and r['vertex_count']==4]
 planes=[]
 for index,r in enumerate(raw_polys):
  verts=[[r['plane_'+str(i+j)] for j in range(3)] for i in range(0,12,3)]
  ab=[verts[1][i]-verts[0][i] for i in range(3)];ac=[verts[2][i]-verts[0][i] for i in range(3)]
  normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
  for addr,body in images:write(addr,body)
  write(code,bytes(native));ok(u.uc_ctl(h,0x4000000a));reg(17,0x2000);reg(5,a4)
  pack(a4+0xe94e-65536,'9h',*(v for vertex in verts[:3] for v in vertex));invoke(code+0xca14)
  planes.append(dict(index=index,vertices=verts,normal=normal,wheels=struct.unpack('>4h',read(a4+0x947e-65536,8))))
 for addr,body in images:write(addr,body)
 recorded=list(struct.unpack('>4h',read(a4+0x947e-65536,8)))
 flags=list(read(a4+0xe94a-65536,2));surface=list(struct.unpack('>9h',read(a4+0xe94e-65536,18)))
 report=dict(scope='Exact pre-contact memory snapshot at first front/rear wheel difference above360. Replay all terrain branches with identical state; not a trajectory test.',recorded=recorded,flags=flags,object_plane=surface,unclipped_object_faces=planes,variants=outputs,matching_recorded=[k for k,v in outputs.items() if list(v)==recorded])
 Path('tmp/c4-jump-plane-replay.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
