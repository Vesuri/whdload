"""Locate actual opponent flag writes before contact."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s)
 for t,e,v in json.loads((ROOT/'tools/fixtures/lap.json').read_text())['events']:
  if t>1050:break
  advance(s,t);s.input(e,v)
 advance(s,1050)
 initial=read_bytes(s,0xa6260,128).hex()
 aux=rd(s,0x8d2c2) if rd(s,0x8d2c0,2)==0x4ef9 else 0x8d2c0
 s.cmd('watch *(unsigned char*)0xa62c8')
 s.cmd('break *0x8747e');s.cmd('condition 2 *(unsigned int*)0xa5d4c >= 1100')
 rows=[]
 for _ in range(1000):
  msg=s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a1 d0 d1')
  pc=int(re.search(r'\bpc\s+0x([0-9a-fA-F]+)',regs)[1],16)
  if pc==0x8747e:break
  rows.append(dict(cursor=rd(s,0xa5d50),field=field(s),pc=hex(pc),registers=regs,actor=read_bytes(s,0xa6260,128).hex(),instructions=s.cmd(f'disassemble {pc-16:#x},{pc+16:#x}'),stop=msg))
 else:raise RuntimeError('flag write limit')
 (s.out/'result.json').write_text(json.dumps(dict(initial=initial,aux=hex(aux),rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('flag writes',len(rows),sorted({r['pc'] for r in rows}),flush=True)
finally:s.quit()
