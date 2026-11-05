import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1);advance(s,310)
 aux=rd(s,0x8d2c2) if rd(s,0x8d2c0,2)==0x4ef9 else 0x8d2c0
 sites={}
 for native in [0x8d3d6,0x8d586,0x8d59e,0x8d5c0,0x8d62a,0x8d630]:
  for addr in {native,aux+native-0x8d2c0}:sites[addr]=native
 for i,addr in enumerate(sites,1):
  s.cmd(f'break *{addr:#x}');s.cmd(f'condition {i} $a1 == 0xa6260')
 s.cmd('break *0x8747e');s.cmd(f'condition {len(sites)+1} *(unsigned int*)0xa5d4c >= 332')
 rows=[]
 for _ in range(500):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a1 a4 a6 d0 d5 d6 d7')
  vals={k:int(v,16) for k,v in re.findall(r'\b(pc|a1|a4|a6|d0|d5|d6|d7)\s+0x([0-9a-fA-F]+)',regs)};pc=vals['pc']
  if pc==0x8747e:break
  assert pc in sites
  rows.append(dict(cursor=rd(s,0xa5d50),live=field(s),native=hex(sites[pc]),registers=vals,dispatch_target=hex(rd(s,vals['a4'])) if sites[pc]==0x8d3d6 else None,actor=read_bytes(s,0xa6260,128).hex(),player=read_bytes(s,0xa5d60,128).hex()))
 else:raise RuntimeError('trace overflow')
 (s.out/'result.json').write_text(json.dumps(dict(aux=hex(aux),rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('branch observations',len(rows),flush=True)
finally:s.quit()
