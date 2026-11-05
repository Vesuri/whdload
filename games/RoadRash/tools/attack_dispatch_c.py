"""Trace actual AI dispatch and lane target before opponent attack selection."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 start,end=1200,1280
 for t,event,value in tape['events']:
  if t>start:break
  advance(s,t);s.input(event,value)
 advance(s,start)
 assert not any(start<t<end for t,_,_ in tape['events'])
 aux=rd(s,0x8d2c2) if rd(s,0x8d2c0,2)==0x4ef9 else 0x8d2c0
 mapping={aux+0x118:0x8d3d8,0x90422:0x90422,0x90494:0x90494,0x90646:0x90646}
 for i,pc in enumerate(mapping,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} $a1 == 0xa6260')
 s.cmd('break *0x8747e');s.cmd(f'condition {len(mapping)+1} *(unsigned int*)0xa5d4c >= {end}')
 rows=[]
 for _ in range(1500):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a1 a2 a4 a6 d0')
  v={k:int(x,16) for k,x in re.findall(r'\b(pc|a1|a2|a4|a6|d0)\s+0x([0-9a-fA-F]+)',regs)}
  if v['pc']==0x8747e:break
  row=dict(native_pc=hex(mapping[v['pc']]),field=field(s),cursor=rd(s,0xa5d50),delta=rd(s,0xa6f00,2),regs=v,subject=read_bytes(s,0xa6260,128).hex(),player=read_bytes(s,0xa5d60,128).hex())
  rows.append(row)
 else:raise RuntimeError('dispatch observation limit')
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('dispatch observations',len(rows),flush=True)
finally:s.quit()
