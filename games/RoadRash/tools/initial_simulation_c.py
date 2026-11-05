import sys,os,json,re
from harness_a import *
s=Session(sys.argv[1])
try:
 s.cmd('break *0x8747e')
 found=False
 for attempt in range(500):
  for value,count in [(1,4),(0,14)]:
   s.input('JOY2_FIRE_BUTTON',value);s.cmd(f'monitor fields {count}',timeout=60)
   regs=s.cmd('info registers pc');pc=int(re.search(r'pc\s+0x([0-9a-fA-F]+)',regs)[1],16)
   if pc==0x8747e:found=True;break
  if found:break
 if not found:raise RuntimeError('initial simulation not reached')
 (s.out/'actors.bin').write_bytes(read_bytes(s,0xa5d60,0x1180))
 (s.out/'rng.bin').write_bytes(read_bytes(s,0x90000,0x88))
 (s.out/'lfsr.bin').write_bytes(read_bytes(s,0xa59f6,4))
 (s.out/'race-state.bin').write_bytes(read_bytes(s,0xa5900,0x2e40))
 result=dict(field=field(s),cursor=rd(s,0xa5d50),delta=rd(s,0xa6f00,2),entry=read_bytes(s,pc,8).hex(),attempt=attempt,provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
