#!/usr/bin/env python3
"""Locate observed simple CPU memory destinations; deliberately partial decoder."""
import json,re,collections,struct
from pathlib import Path
import capstone
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=Path('tmp/prof/render-beam-fast');m=json.loads((p/'anchor.json').read_text());mem=(p/'memory.bin').read_bytes();t=barto.load(p/'trace.bin');md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000);cache={};sites={}
report=json.loads((p/'render-beam-check.json').read_text());ranges=[(plane,plane+8000,c) for c,v in report['bitmap_maps'].items() for plane in v['planes']]
for f in t.fields[2:4]:
 for order,(pc,c,r) in enumerate(t.instructions(f)):
  if pc is None or pc==0x7fffffff:continue
  if pc not in cache:
   if m['memory_base']<=pc<m['memory_base']+len(mem):data=mem[pc-m['memory_base']:pc-m['memory_base']+22]
   elif 0<=pc<len(t.chip):data=t.chip[pc:pc+22]
   else:cache[pc]=None;continue
   ins=next(md.disasm(data,pc),None);cache[pc]=ins
  ins=cache[pc]
  if ins is None or not ins.mnemonic.startswith(('move.','clr.','or.','and.','eor.','add.','sub.','not.')):continue
  dst=ins.op_str.split(', ')[-1];a=None
  match=re.fullmatch(r'\(a([0-7])\)\+?',dst)
  if match:a=r[8+int(match[1])]
  match=re.fullmatch(r'(-?)\$([0-9a-f]+)\(a([0-7])\)',dst)
  if match:a=(r[8+int(match[3])]+(-1 if match[1] else 1)*int(match[2],16))&0xffffffff
  match=re.fullmatch(r'\$([0-9a-f]+)\.l',dst)
  if match:a=int(match[1],16)
  if a is None:continue
  owners=[c for lo,hi,c in ranges if lo<=a<hi]
  if not owners and not 0xdff040<=a<=0xdff074:continue
  k=hex(pc);site=sites.setdefault(k,dict(offset=hex(pc-m['game_base']),instruction=ins.mnemonic+' '+ins.op_str,count=0,examples=[]));site['count']+=1
  if len(site['examples'])<4:site['examples'].append(dict(field=f.index,order=order,address=hex(a),copper=owners,registers=r))
out=dict(scope='Only simple CPU destinations for selected opcodes in fields2/3; not complete write coverage or timing proof.',sites=sites)
(p/'render-write-sites.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
