from pathlib import Path
import re,json,struct,sys
from capstone import *
from capstone.m68k import *
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-b6-s5/lean';code=(b/'fine.bin').read_bytes();listing=(b/'fine.list').read_text();mapping=json.loads((r/'manifest/step2-overlays.json').read_text());ranges=[h for g in mapping['groups'] for h in g['hunks'] if h['size']];c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020);c.detail=True
rows=[]
for line in listing.splitlines():
 m=re.match(r'00:([0-9A-F]{8})\s+[0-9A-F]+\s+\d+:\s+(.*)',line)
 if not m:continue
 pc=int(m[1],16);src=m[2].strip()
 if src.startswith(('dc.','ds.','incbin')):continue
 ins=list(c.disasm(code[pc:pc+24],pc,count=1))
 if not ins:continue
 i=ins[0]
 for operand in i.operands:
  if operand.type not in (M68K_OP_MEM,M68K_OP_IMM):continue
  value=operand.imm&0xffffffff
  hs=[h for h in ranges if h['base']<=value<h['base']+h['size']]
  if hs:rows.append(dict(pc=pc,src=src,operand_type=operand.type,address_mode=operand.address_mode,value=hex(value),hunk=hs[0]['number']))
(r/'manifest/step5-b7-binding-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
print('references',len(rows));print('\n'.join(str(x) for x in rows if x['operand_type']==M68K_OP_IMM))
