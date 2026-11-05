"""Capture opponent curve operands before normalization at identical lap input."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);tape=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
 for t,e,v in tape['events']:
  if t>620:break
  advance(s,t);s.input(e,v)
 advance(s,620)
 code=rd(s,0x8b488) if rd(s,0x8b486,2)==0x4ef9 else 0x8b486
 bp=code+0x8bcd0-0x8b486
 (s.out/'native-road.txt').write_text(s.cmd('disassemble 0x8bc00,0x8bd70'))
 s.cmd(f'break *{bp:#x}');s.cmd('condition 1 $a1 == 0xa6260')
 s.cmd('break *0x8747e');s.cmd('condition 2 *(unsigned int*)0xa5d4c >= 790')
 rows=[]
 for _ in range(1000):
  s.cmd('continue',timeout=60);regs=s.cmd('info registers pc d1 d6 a1')
  v={k:int(x,16) for k,x in re.findall(r'\b(pc|d1|d6|a1)\s+0x([0-9a-fA-F]+)',regs)}
  if v['pc']==0x8747e:break
  rows.append(dict(cursor=rd(s,0xa5d50),field=field(s),regs=v,delta=rd(s,0xa6f00,2),actor=read_bytes(s,0xa6260,128).hex()))
 else:raise RuntimeError('road probe limit')
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('road samples',len(rows),flush=True)
finally:s.quit()
