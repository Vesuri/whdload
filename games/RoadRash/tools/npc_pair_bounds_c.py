"""Observe computed contact bounds before penetration and response."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 for target,event,value in tape['events']:
  if target>1050:break
  advance(s,target);s.input(event,value)
 advance(s,1050)
 copy=rd(s,0x8b488) if rd(s,0x8b486,2)==0x4ef9 else 0x8b486
 mapping={pc:a for a in [0x8c9c4,0x8caee,0x8cb68] for pc in {a,copy+a-0x8b486}}
 (s.out/'collision.txt').write_text(s.cmd('disassemble 0x8c8ae,0x8cb70'))
 for i,pc in enumerate(mapping,1):
  s.cmd(f'break *{pc:#x}');s.cmd(f'condition {i} ($a1 == 0xa61e0 && $a2 == 0xa6260) || ($a1 == 0xa6260 && $a2 == 0xa61e0)')
 s.cmd('break *0x8747e');s.cmd(f'condition {len(mapping)+1} *(unsigned int*)0xa5d4c >= 1100')
 rows=[]
 for _ in range(300):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a0 a1 a2 d0 d1')
  values={k:int(v,16) for k,v in re.findall(r'\b(pc|a0|a1|a2|d0|d1)\s+0x([0-9a-fA-F]+)',regs)}
  if values['pc']==0x8747e:break
  rows.append(dict(native_pc=hex(mapping[values['pc']]),field=field(s),cursor=rd(s,0xa5d50),registers=regs,subject=read_bytes(s,values['a1'],128).hex(),other=read_bytes(s,values['a2'],128).hex(),steering=rd(s,0xa7262,2),delta=rd(s,0xa6f00,2)))
 else:raise RuntimeError('too many contacts')
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('collision bound observations',len(rows),flush=True)
finally:s.quit()
