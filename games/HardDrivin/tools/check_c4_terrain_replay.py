"""Replay recorded zero-contact terrain inputs against optimized and native code."""
from pathlib import Path
import ctypes as C,json,os,random,re,struct,subprocess,sys
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0x9b0000,7));ok(u.uc_mem_map(h,0x7800000,0x800000,7))
sys.path.insert(0,'tools')
from game_image import hunks
from machine_profiles import banks
root=Path('tmp/prof/c4-loop-racing-060');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base'];stop=0x41000;sp=0x4f000
images=[(addr,(root/f'timing-state-{name}.bin').read_bytes()) for name,addr,size in banks(meta['configuration'])]
hs=hunks();native=bytearray(hs[0]['data']);bases=[r['base'] for r in lay['regions']]
for off,dest in hs[0]['relocs']:struct.pack_into('>I',native,off,struct.unpack_from('>I',native,off)[0]+bases[dest])
rows=json.loads((root/'motion.json').read_text())['rows'];target=next(r for r in rows if r['kind']=='STEP' and r['mask']==0)
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
  for short,long,k in [(0x98f6,0x98fc,'x8'),(0x98f8,0x9900,'y8'),(0x98fa,0x9904,'z8')]:
   pack(a4+long-65536,'i',target[k]);pack(a4+short-65536,'h',target[k]//8)
  pack(a4+0x98e4-65536,'I',target['road_cursor']);pack(a4+0x9950-65536,'B',1)
  for off,k in [(0x9448,'sin_yaw'),(0x944a,'cos_yaw'),(0x944c,'sin_pitch'),(0x944e,'cos_pitch')]:pack(a4+off-65536,'h',target[k])
  for off,func in [(0x9450,a4-0x7f26),(0x9452,a4-0x7f2c)]:invoke(func,target['roll']);pack(a4+off-65536,'h',reg(9)&65535 if reg(9)&32768==0 else (reg(9)&65535)-65536)
  invoke(code+entry)
  wheel=struct.unpack('>4h',read(a4+0x947e-65536,8));outputs[name]=wheel
 recorded=[target[k] for k in ['wheel_fl','wheel_fr','wheel_rl','wheel_rr']]
 report=dict(scope='Reconstructed zero-contact pose and exact captured yaw/pitch trig, with native roll trig. Compare terrain branches at the same pose; not a full physics or route test.',field=target['field'],road_flag=target['road'],recorded=recorded,variants=outputs,road_code_equivalent=outputs['optimized_road']==outputs['native_road'],matching_recorded=[k for k,v in outputs.items() if list(v)==recorded])
 report['branch_difference_reproduced']=bool(report['matching_recorded']) and report['road_code_equivalent'] and list(outputs['native_road'])!=recorded
 Path('tmp/c4-terrain-replay.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
