import sys,json,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 (s.out/'initial.bin').write_bytes(read_bytes(s,0xa5900,0x2e40))
 (s.out/'initial-rng.bin').write_bytes(read_bytes(s,0x90000,0x88))
 for t,k,v in json.loads((ROOT/'tools/fixtures/c-attacks.json').read_text())['events']:
  if t>1450:break
  advance(s,t);s.input(k,v)
 advance(s,1450)
 target=rd(s,0x875b8);code=read_bytes(s,target,128);off=code.find(bytes.fromhex('4eb90008eff84e75'));assert off>=0
 bp=target+off+6;s.cmd(f'break *{bp:#x}')
 main=rd(s,0x87480);data=read_bytes(s,main,1024);off=data.find(b'RRCSTEP1');assert off>=0;base=main+off
 cursors=[]
 for i in range(40):
  s.cmd('continue',timeout=60);cursor=rd(s,base+8);cursors.append(cursor)
  assert cursor<=1457,cursors
  if cursor==1457:break
 else:raise RuntimeError(cursors)
 (s.out/'step1457.bin').write_bytes(read_bytes(s,0xa5900,0x2e40))
 (s.out/'boundary.json').write_text(json.dumps(dict(cursors=cursors,stats=struct.unpack('>4I',read_bytes(s,base+8,16)),provenance=provenance(os.environ['SLAVE'],s)),indent=2));print(cursors,flush=True)
finally:s.quit()
