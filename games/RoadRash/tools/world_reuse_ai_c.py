import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 tape=json.loads((ROOT/'tools/fixtures/c-attacks.json').read_text())
 for target,event,value in tape['events']:
  if target>1200:break
  advance(s,target);s.input(event,value)
 advance(s,1200)
 listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
 sy={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)$',listing,re.M)}
 base=rd(s,0x87480)-sy['step_main']
 sites=[base+sy['aux_8d2c0']+pc-0x8d2c0 for pc in [0x8d766,0x8d792]]+[0x8db70,0x8dba6]
 for i,pc in enumerate(sites,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} *(unsigned int*)0xa5d50 == 1239 && $a1 == 0xa61e0')
 s.cmd('break *0x87598');s.cmd('condition 5 *(unsigned int*)0xa5d50 == 1239')
 rows=[]
 for _ in range(10):
  s.cmd('continue',timeout=60)
  regs=s.cmd('info registers')
  rows.append(dict(registers=regs,cursor=rd(s,0xa5d50),lane=read_bytes(s,0x8d00a,0x140).hex(),stack=read_bytes(s,int(re.search(r'(?:a7|sp)\s+0x([0-9a-fA-F]+)',regs)[1],16),32).hex()))
  if re.search(r'pc\s+0x87598\b',regs):break
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('cursors',[r['cursor'] for r in rows],flush=True)
finally:s.quit()
