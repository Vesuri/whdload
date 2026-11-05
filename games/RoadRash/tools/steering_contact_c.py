"""Observe collision-driven steering writes during the first long left turn."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 for target,event,value in tape['events']:
  if target>1200:break
  advance(s,target);s.input(event,value)
 advance(s,1200)
 copy=rd(s,0x8b488) if rd(s,0x8b486,2)==0x4ef9 else 0x8b486
 mapping={copy+a-0x8b486:a for a in [0x8c25e,0x8c36c]}
 for i,pc in enumerate(mapping,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} $a1 == 0xa5d60')
 s.cmd('break *0x8747e');s.cmd('condition 3 *(unsigned int*)0xa5d4c >= 1400')
 rows=[]
 for _ in range(200):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a0 a1 a2 d0')
  values={k:int(v,16) for k,v in re.findall(r'\b(pc|a0|a1|a2|d0)\s+0x([0-9a-fA-F]+)',regs)}
  if values['pc']==0x8747e:break
  rows.append(dict(native_pc=hex(mapping[values['pc']]),field=field(s),cursor=rd(s,0xa5d50),registers=regs,player=read_bytes(s,0xa5d60,128).hex(),other=read_bytes(s,values['a2'],128).hex(),steering=rd(s,0xa7262,2)))
 else:raise RuntimeError('too many contacts')
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('steering contacts',[(r['field'],r['native_pc']) for r in rows],flush=True)
finally:s.quit()
