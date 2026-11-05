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
 sites=[0x87486,base+sy['aux_8da5c'],0x87592]
 for i,pc in enumerate(sites,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} *(unsigned int*)0xa5d50 == 1239')
 rows=[]
 for _ in range(50):
  s.cmd('continue',timeout=60)
  regs=s.cmd('info registers')
  rows.append(dict(registers=regs,cursor=rd(s,0xa5d50),lane=read_bytes(s,0x8d00a,0x140).hex()))
  if re.search(r'pc\s+0x87592\b',regs):break
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2))
 print('cursors',[r['cursor'] for r in rows],flush=True)
finally:s.quit()
