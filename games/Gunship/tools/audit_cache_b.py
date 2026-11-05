#!/usr/bin/env python3
"""Static control-flow/write inventory, augmented by the retained A scene profiles."""
import json,re,struct,collections
from pathlib import Path
import _amigaxdev
from capstone import *
from amitools.binfmt.BinFmt import BinFmt
from amitools.binfmt.Relocate import Relocate
from amigaxdev import aprof
root=Path(__file__).resolve().parents[1];out=root/'tmp/b';base=0x200000
img=BinFmt().load_image(str(root/'tmp/game/Gunship/data/gamemule'))
b=bytes(Relocate(img).relocate([base+i*0x20000 for i in range(9)])[0])
md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000);md.detail=True
# Documented OS callbacks and formatter callback, plus keyboard dispatch vector.
seeds={0,0x1a0,0xd60,0xf14,0xc764,0xe890}
seeds.update(x-base for x in struct.unpack_from('>19I',b,0xdb4))
observed=set();profiles=[]
for p in (root/'tmp/a-final').rglob('window.prof'):
 layout=json.loads((p.parent/'layout.json').read_text());gb=layout['hunks'][0]
 h,pcs,n=aprof.parse_profile(p.read_text());observed.update(pc-gb for pc in pcs if gb<=pc<gb+len(b));profiles.append(str(p.relative_to(root)))
seeds.update(observed)
seen={};unresolved=[];todo=list(seeds)
while todo:
 pc=todo.pop()
 while 0<=pc<len(b) and pc not in seen:
  i=next(md.disasm(b[pc:pc+24],base+pc,count=1),None)
  if not i or i.mnemonic.startswith('dc.'):break
  seen[pc]=i
  name=i.mnemonic.split('.')[0];target=None
  if 1 in i.groups:
   op=i.operands[-1]
   if op.type==8:target=pc+2+op.br_disp.disp
   elif op.address_mode in (16,17):target=op.imm-base
   elif op.address_mode==11:target=pc+2+op.mem.disp
   elif name in ('jsr','jmp') and not(op.address_mode==6 and op.mem.base_reg==15):unresolved.append((hex(pc),i.mnemonic,i.op_str))
   if target is not None and 0<=target<len(b):todo.append(target)
  if name in ('rts','rte','rtr','jmp','bra'):break
  # Inline words after calls to this original helper are parameters, not opcodes.
  if name=='jsr' and target==0x5a10:pc+=2
  pc+=i.size
# Independently decoded direct writes in the full disassembly; the listing retains
# padding/data as well, so operands and targets are reviewed against the data map.
rows=[]
for l in (root/'tmp/analysis/gamemule.dis').read_text().splitlines():
 t=re.split(r'  +',l.strip())[-1];name=t.split(' ')[0].split('.')[0]
 if name not in ('move','movem','clr','st','sf','seq','sne','smi','spl','add','addq','addi','sub','subq','subi','and','andi','or','ori','eor','eori','lsl','lsr','asl','asr','rol','ror','roxl','roxr','bset','bclr','bchg','not','neg','negx','tas'):continue
 m=re.search(r'(?:,| )0x([0-9a-f]+)$',t)
 if m and 0<=int(m[1],16)-0x985cd8<len(b):rows.append(dict(pc=int(l[:5],16),target=int(m[1],16)-0x985cd8,instruction=t))
fetch={x for pc,i in seen.items() for x in range(pc,pc+i.size)}
# Writable islands: end exclusive. CPU data only. Includes indirect writes.
ranges=[(0xc64,0xc78),(0xc8e,0xd4c),(0x4b18,0x4b1c),(0x4e18,0x4e3b),(0x5518,0x5526),(0x5af6,0x5afa),(0x5afe,0x5b04),(0x5b22,0x5b24),(0x6980,0x77b8),(0x8524,0x8530),(0x8d88,0x90b0),(0x9c44,0x9c58),(0xa14c,0xa14e),(0xa434,0xa450),(0xa99c,0xaa4a),(0xaf8c,0xafa4),(0xb048,0xb05e),(0xb1ba,0xb1c3),(0xb1dc,0xb278),(0xb6ec,0xb70c),(0xb92c,0xba10),(0xba34,0xba64),(0xc6a0,0xc762)]
missing=[r for r in rows if not any(a<=r['target']<z for a,z in ranges)]
intersections=[hex(x) for a,z in ranges for x in range(a,z) if x in fetch]
report=dict(direct_write_sites=len(rows),distinct_direct_targets=len({r['target'] for r in rows}),reachable_instructions=len(seen),observed_pcs=len(observed),profiles=profiles,unmapped_writes=missing,code_data_overlap=intersections,indirect_control_flow=unresolved,unreached_write_sites=[hex(r['pc']) for r in rows if r['pc'] not in seen],ranges=[[hex(a),hex(z)] for a,z in ranges],writes=rows)
(out/'cache-audit.json').write_text(json.dumps(report,indent=2))
print({k:v for k,v in report.items() if k not in ('writes','profiles','ranges')})
