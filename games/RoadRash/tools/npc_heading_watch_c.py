"""Locate actual opponent heading writes before contact."""
import json,os,re,sys
from harness_a import *
s=Session(sys.argv[1])
try:
 route(s);(s.out/'heading-helper.txt').write_text(s.cmd('disassemble 0x8cef0,0x8d006'));s.input('JOY2_UP',1);advance(s,300)
 s.cmd('watch *(unsigned short*)0xa6268')
 s.cmd('break *0x8747e');s.cmd('condition 2 *(unsigned int*)0xa5d4c >= 410')
 rows=[]
 for _ in range(250):
  msg=s.cmd('continue',timeout=60);regs=s.cmd('info registers pc a1 d0 d1')
  pc=int(re.search(r'\bpc\s+0x([0-9a-fA-F]+)',regs)[1],16)
  if pc==0x8747e:break
  rows.append(dict(cursor=rd(s,0xa5d50),field=field(s),pc=hex(pc),registers=regs,actor=read_bytes(s,0xa6260,128).hex(),instructions=s.cmd(f'disassemble {pc-16:#x},{pc+16:#x}'),stop=msg))
 else:raise RuntimeError('heading write limit')
 (s.out/'result.json').write_text(json.dumps(dict(rows=rows,provenance=provenance(os.environ['SLAVE'],s)),indent=2)+'\n');print('heading writes',len(rows),sorted({r['pc'] for r in rows}),flush=True)
finally:s.quit()
