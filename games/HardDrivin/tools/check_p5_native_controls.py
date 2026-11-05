from pathlib import Path
import ctypes as C,json,os,random,re,struct,subprocess,sys
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0x50000,0xfb0000,7));sys.path.insert(0,'tools');from game_image import hunks
bases=[0x100000,0x200000,0x300000];a4=bases[1]+0x7ffe
for j,hu in enumerate(hunks()):
 b=bytearray(hu['data'])
 for off,dest in hu['relocs']:struct.pack_into('>I',b,off,struct.unpack_from('>I',b,off)[0]+bases[dest])
 write(bases[j],bytes(b))
sy=[]
for idx in [0,1]:
 p=Path(f'tmp/p5-ramps-{idx}');write(0x2c000+idx*0x1000,p.with_suffix('.bin').read_bytes());sy.append({n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',p.with_suffix('.lst').read_text(),re.M)})
# Keyboard empty; startup sound is recorded, not delivered to hardware.
write(a4-0x7f92,bytes.fromhex('70004e75'));write(a4-0x7fce,bytes.fromhex('52b9000303004e75'))
saved=read(bases[1],31948);stop=0x60000;sp=0x5f000;write(stop,bytes.fromhex('40f900030304'));rng=random.Random(509)
try:
 for case in range(12000):
  n=rng.randrange(65536);carry=rng.randint(-65535,65535);throttle=rng.randrange(101);last=rng.randrange(101);buttons=rng.randrange(8);mode=rng.randint(1,3);gates=[rng.choice([0,0,255]) for _ in range(3)];outs=[]
  for idx in [0,1]:
   write(bases[1],saved);write(0x30000,bytes(0x308));pack(0x30004,'i',carry);write(0x30008,bytes([last]));pack(0x30100,'H',n)
   for off,v in [(-0x66e4,throttle),(-0x69fa,gates[0]),(-0x69fc,gates[1]),(-0x5224,255),(-0x5223,0),(-0x5222,6),(-0x6864,gates[2]),(-0x6a08,mode)]:write(a4+off,bytes([v]))
   pack(a4-0x6a0a,'H',buttons)
   for off,name,size in [(0x7d36,'_time_throttle_up',10),(0x7d50,'_time_throttle_down',8)]:write(bases[0]+off,bytes.fromhex('4eb9')+struct.pack('>I',sy[idx][name])+bytes.fromhex('4e71')*((size-6)//2))
   reg(17,0x2000|case%32)
   for k in range(1,17):reg(k,k*0x10101)
   reg(5,a4);reg(8,sp);pack(sp,'I',stop)
   ok(u.uc_emu_start(h,bases[0]+0x7c32,stop,1000000,20000));assert reg(18)==stop
   ok(u.uc_emu_start(h,stop,stop+6,1000000,1));outs.append((read(bases[1],31948),read(0x30000,0x308),[reg(k) for k in range(1,17) if k not in [1,2,10]]))
  assert outs[0]==outs[1],(case,n,throttle,buttons,gates)
 report=dict(passed=True,cases=12000,scope='Complete native 7C32 controls with old/new throttle hooks: both buttons, all gear-selection mouse modes, crash, timeout and latch gates, unsigned intervals and fractional carries; all game globals, companion state, sound count, returned D0/CCR and callee-saved registers match.')
 Path('tmp/p5-native-controls-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
