from pathlib import Path
import ctypes as C,json,os,random,struct,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
s=Path('tools/c4_terrain_road.s').read_text();body=s[s.index('_private_road_selected_hook:'):s.index('_private_road_selected:')]
for name,addr,text in [('hook',0x10000,body+'\n_private_road_selected equ $11000'),('native',0x12000,' move.l a2,-70(a5)\n move.w d5,-62(a5)\n rts')]:
 stem=Path('tmp/c4-road-hook-'+name);stem.with_suffix('.s').write_text(f' org ${addr:x}\n'+text+'\n');subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(addr,stem.with_suffix('.bin').read_bytes())
rng=random.Random(1713);count=0
try:
 for case in range(256):
  initial={k:rng.getrandbits(32) for k in range(1,17)};initial[6]=0x30000;initial[8]=0x4f000;initial[13]=case%2+1;sr=0x2000+(case%32);outputs=[]
  for addr in [0x10000,0x12000]:
   write(0x2ff00,bytes(256));reg(17,sr)
   for k,v in initial.items():reg(k,v)
   pack(0x4f000,'I',0x19000);ok(u.uc_emu_start(h,addr,0x19000,1000000,1000));assert reg(18)==0x19000
   outputs.append(([reg(k) for k in range(1,18)],read(0x2ff00,256)))
  assert outputs[0]==outputs[1],case
  assert struct.unpack('>H',read(0x11000,2))[0]==initial[13]
  count+=1
 report=dict(passed=True,cases=count,scope='Assembled selection hook versus displaced native instructions: all registers, final condition codes, stack and native local writes agree; selected candidate is recorded.')
 Path('tmp/c4-road-hook-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
