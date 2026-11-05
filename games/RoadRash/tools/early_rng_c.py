import sys,json,os,re
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);s.input('JOY2_UP',1)
 (s.out/'rng-code.txt').write_text(s.cmd('disassemble 0x90088,0x901a0'))
 (s.out/'initial-rng.bin').write_bytes(read_bytes(s,0x90000,0x88))
 s.cmd('break *0x900ce');s.cmd('break *0x8747e');s.cmd('condition 2 *(unsigned int*)0xa5d4c >= 580')
 rows=[]
 for _ in range(4000):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a1 sp')
  v={k:int(x,16) for k,x in re.findall(r'\b(pc|a1|sp)\s+0x([0-9a-fA-F]+)',regs)}
  if v['pc']==0x8747e:break
  rows.append(dict(cursor=rd(s,0xa5d50),live=field(s),actor=hex(v['a1']),caller=hex(rd(s,v['sp'])),delta=rd(s,0xa6f00,2)))
 else:raise RuntimeError('RNG call limit')
 result=dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s));(s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('RNG calls',len(rows),flush=True)
finally:s.quit()
