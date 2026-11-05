from pathlib import Path
import json,os,random,re,struct,subprocess
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
p=Path('tmp/p5-road-scan');subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(0x400100,p.with_suffix('.bin').read_bytes())
ok(u.uc_mem_map(h,0x600000,0x300000,7))
stop=0x490000;sp=0x4ffff0;write(stop,bytes.fromhex('40f900480000'));rng=random.Random(515);saved=read(database,31948)
try:
 for case in range(12003):
  counts=([65535,0] if case==12000 else [0,65535] if case==12001 else [65535,65535] if case==12002 else [rng.randrange(33),rng.randrange(33)]);pos=[rng.choice([0,1,32767,32768,65535,rng.randrange(65536)]) for _ in range(3)];roads=[]
  for count in counts:
   rows=[]
   for j in range(count):
    row=[rng.randrange(65536) for _ in range(10)]
    if case%3==0:row[:3]=[rng.choice([v,(v+32768)&65535,0]) for v in pos]
    if j and case%5==0:row=rows[-1][:]
    rows.append(row)
   roads.append(b''.join(struct.pack('>10H',*v) for v in rows))
  regs=[rng.randrange(1<<32) for _ in range(17)];oldtype=rng.randrange(256);outputs=[]
  for code in [codebase+0x4eb2,0x400100]:
   write(database,saved);write(0x600000,roads[0] or bytes(20));write(0x740000,roads[1] or bytes(20));pack(a4-0x6720,'I',0x600000);pack(a4-0x66ae,'I',0x740000);pack(a4-0x6718,'H',counts[0]);pack(a4-0x66aa,'H',counts[1]);pack(a4-0x6710,'3H',*pos);write(a4-0x66b0,bytes([oldtype]));reg(17,0x2000|case%32)
   for k in range(1,17):reg(k,regs[k])
   reg(5,a4);reg(8,sp);pack(sp,'I',stop)
   ok(u.uc_emu_start(h,code,stop,0,12000000));assert reg(18)==stop
   ok(u.uc_emu_start(h,stop,stop+6,1000000,1));outputs.append((read(database,31948),[reg(k) for k in range(1,17)],read(0x480000,2)))
  assert outputs[0]==outputs[1],(case,counts,pos,[(j,x,y) for j,(x,y) in enumerate(zip(outputs[0][1],outputs[1][1])) if x!=y],outputs[0][2],outputs[1][2])
 report=dict(passed=True,cases=12003,bytes=p.with_suffix('.bin').stat().st_size,scope='Actual original 4EB2 vs optimized whole scan: two road lists, empty lists, ties, signed-word extremes and distance overflow; all game data, every D/A register, stack and materialized CCR exact.')
 Path('tmp/p5-road-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
