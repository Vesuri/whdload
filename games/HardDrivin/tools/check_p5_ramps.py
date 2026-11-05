from pathlib import Path
import re,struct,random,json,os,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0x50000,0xfb0000,7));r=Path('src');old=Path('tmp/p5-before');symbols=[]
t=(r/'HardDrivinTime.s').read_text();helper=t[t.index('_time_scale_word:'):t.index('; Exact signed-long times unsigned-word')]
for idx,root in enumerate([old,r]):
 s=(root/'HardDrivinScalar.s').read_text();equ='\n'.join(l for l in s.splitlines() if re.match(r'SS_.* equ ',l))+'\n'
 # Scalar state equates live in Time.s in some revisions.
 for p in r.glob('*.s'):
  for l in p.read_text(encoding='latin1').splitlines():
   if re.match(r'SS_.* equ ',l) and l not in equ:equ+=l+'\n'
 block=s[s.index('_time_throttle_up:'):s.index('_time_collision_velocity:')]
 src=f' org ${0x2c000+idx*0x1000:x}\n_time_scalar_state equ $30000\n_time_scalar_fields equ $30100\n'+equ+block+helper
 stem=Path(f'tmp/p5-ramps-{idx}');stem.with_suffix('.s').write_text(src)
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 write(0x2c000+idx*0x1000,stem.with_suffix('.bin').read_bytes());symbols.append({n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+A:([0-9A-F]+)',stem.with_suffix('.lst').read_text(),re.M)})
a4=0x70000;stop=0x60000;sp=0x5f000;write(stop,bytes.fromhex('40f900030200'));rng=random.Random(506);total=0
try:
 for name,value in [('_time_throttle_up',100),('_time_throttle_down',0)]:
  for case in range(75536):
   n=case if case<65536 else rng.randrange(65536);v=value if case<65536 else rng.randrange(256);carry=0 if case<65536 else rng.randint(-65535,65535);last=rng.randrange(256);regs=[rng.randrange(1<<32) for _ in range(17)];outs=[]
   for sy in symbols:
    write(0x30000,bytes(0x204));pack(0x30004,'i',carry);write(0x30008,bytes([last]));pack(0x30100,'H',n);write(a4-0x66e4,bytes([v]));reg(17,0x2000|case%32)
    for k in range(1,17):reg(k,regs[k])
    reg(5,a4);reg(8,sp);pack(sp,'I',stop)
    ok(u.uc_emu_start(h,sy[name],stop,1000000,1000));assert reg(18)==stop
    ok(u.uc_emu_start(h,stop,stop+6,1000000,1));outs.append(([reg(k) for k in range(1,17) if k not in [1,9,10]],read(0x30000,0x204),read(a4-0x66e4,1)))
   assert outs[0]==outs[1],(name,n,v,carry,last,[(i,x,y) for i,(x,y) in enumerate(zip(outs[0][1],outs[1][1])) if x!=y],outs[0][2],outs[1][2]);total+=1
 report=dict(passed=True,cases=total,scope='Both throttle directions, every unsigned interval at saturation with zero debt, plus 20000 random byte values/fractions/stale companions; callee-saved registers, stack, throttle/companion and materialized CCR exact.')
 Path('tmp/p5-controls-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
