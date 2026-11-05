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
for name,distances in [('recorded',[525,525,-735,-735]),('finite_object_with_ground',[193,193,182,3]),('road',[6,6,1,1])]:
 for addr,body in images:write(addr,body)
 ok(u.uc_ctl(h,0x4000000a));reg(17,0x2000);reg(5,a4)
 pack(a4+0x947e-65536,'4h',*distances);invoke(code+0xcab6)
 rates=None
 for addr,body in images:
  index=body.find(b'HDCRATE1')
  if index>=0:rates=struct.unpack('>4i',read(addr+index+8,16))
 outputs[name]=dict(mask=read(a4+0x9910-65536,1)[0],pitch=struct.unpack('>h',read(a4+0x994c-65536,2))[0],roll=struct.unpack('>h',read(a4+0x994e-65536,2))[0],rates=rates)
report=dict(scope='Isolated captured optimized contact response to alternate wheel distances at the same jump state. Tests response only; no new terrain policy is accepted.',variants=outputs)
Path('tmp/c4-finite-contact-response.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
