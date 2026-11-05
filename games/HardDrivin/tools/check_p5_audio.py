from pathlib import Path
import re,struct,random,json,os,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0x50000,0xfb0000,7));r=Path('src');old=Path('tmp/p5-before');symbols=[]
for idx,root in enumerate([old,r]):
 s=(root/'HardDrivinAudio.s').read_text();equ='\n'.join(l for l in s.splitlines() if re.match(r'AU_.* equ ',l))+'\n'
 block=s[s.index('_audio_offroad:'):s.index('_audio_skid:')]+s[s.index('_audio_due:'):s.index('\n\tIFD VERIFY_AUDIO_MATH',s.index('_audio_due:'))]
 src=f' org ${0x2c000+idx*0x1000:x}\n_dispatch_state equ $30000\n_replay_state equ $30100\n_audio_offroad_state equ $30200\nDS_ACTIVE equ 24\nDS_STEPS equ 8\nRP_WALL equ 0\n'+equ+block
 stem=Path(f'tmp/p5-audio-{idx}');stem.with_suffix('.s').write_text(src)
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 write(0x2c000+idx*0x1000,stem.with_suffix('.bin').read_bytes());symbols.append({n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',stem.with_suffix('.lst').read_text(),re.M)})
a4=0x70000;stop=0x60000;sp=0x5f000;write(stop,bytes.fromhex('40f900030400'))
# Observe native entry CCR and argument; handler deliberately clobbers scratch.
write(a4-0x7fce,bytes.fromhex('4ef900060100'))
write(0x60100,bytes.fromhex('40f90003040233ef00040003040452b9000304087011722241f90005123443f9000543214e75'))
rng=random.Random(507)
try:
 for case in range(16000):
  state=bytearray(rng.randbytes(0x500));state[24]=rng.choice([0,255]);step=rng.randrange(1<<32);wall=rng.randrange(1<<32);struct.pack_into('>I',state,8,step);struct.pack_into('>I',state,0x100,wall);struct.pack_into('>II',state,0x200,(wall-rng.randrange(32))&0xffffffff,(step-rng.randrange(4))&0xffffffff);state[0x210]=rng.choice([0,255]);regs=[rng.randrange(1<<32) for _ in range(17)];outs=[]
  for sy in symbols:
   write(0x30000,bytes(state));reg(17,0x2000|case%32)
   for k in range(1,17):reg(k,regs[k])
   reg(5,a4);reg(8,sp);pack(sp,'I',stop)
   ok(u.uc_emu_start(h,sy['_audio_offroad'],stop,1000000,1000));assert reg(18)==stop
   ok(u.uc_emu_start(h,stop,stop+6,1000000,1));outs.append(([reg(k) for k in range(1,17) if k not in [1,2,9,10]],read(0x30000,0x500)))
  assert outs[0]==outs[1],(case,[(i,x,y) for i,(x,y) in enumerate(zip(outs[0][1],outs[1][1])) if x!=y])
 report=dict(passed=True,cases=16000,scope='Off-road audio emit/skip/inactive episodes, wrapped wall/step counters; exact requests, cadence state, sound arguments, native-entry and return CCR, stack and callee-saved registers. Native caller scratch excluded.')
 Path('tmp/p5-audio-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
