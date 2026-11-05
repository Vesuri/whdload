import sys,json,os,re
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for t,e,v in json.loads((ROOT/'tools/fixtures/lap.json').read_text())['events']:
  if t>1050:break
  advance(s,t);s.input(e,v)
 advance(s,1050)
 aux=rd(s,0x8d2c2) if rd(s,0x8d2c0,2)==0x4ef9 else 0x8d2c0
 sites=sorted({0x8d5f8,aux+0x338})
 for i,pc in enumerate(sites,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} $a1 == 0xa6260 && (*(unsigned char*)0xa62c8 & 4) != 0')
 s.cmd('break *0x8747e');s.cmd(f'condition {len(sites)+1} *(unsigned int*)0xa5d4c >= 1100')
 s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a1');pc=int(re.search(r'pc\s+0x([0-9a-fA-F]+)',regs)[1],16)
 result=dict(found=pc!=0x8747e,pc=hex(pc),cursor=rd(s,0xa5d50),live=field(s),provenance=provenance(os.environ['SLAVE'],s))
 if result['found']:
  result['instruction']=read_bytes(s,pc,6).hex();result['before']=read_bytes(s,0xa62c8,1).hex();s.cmd('stepi');result['after']=read_bytes(s,0xa62c8,1).hex()
 (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
finally:s.quit()
