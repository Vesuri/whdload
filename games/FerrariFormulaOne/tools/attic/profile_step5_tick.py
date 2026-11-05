from pathlib import Path
import sys,collections,json,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];t=barto.load(r/'tmp/step3/detail-a1200-c1/detail.bin')
lines=(r/'tmp/step4/active.dis').read_text().splitlines();instructions={int(s[:6],16):s for s in lines if re.match('[0-9a-f]{6}:',s)}
funcs=[(0x67120,0x6872e,'car body'),(0x6872e,0x6a200,'AI/contact helpers'),(0x6cd00,0x6d4cc,'engine force helpers'),(0x6d4cc,0x6dc38,'drag/RPM/gear'),(0x6dc38,0x6e2a0,'velocity/slip/tyre response'),(0x6ea3e,0x6ec94,'wear'),(0x6ec94,0x6ef20,'failure helpers'),(0x293d0,0x29412,'software long division'),(0x29500,0x29542,'software signed multiply'),(0x24fe0,0x25020,'sin/cos'),(0x25770,0x257ac,'sqrt')]
active=False;groups=collections.Counter();pcs=collections.Counter();calls=collections.Counter();divargs=collections.Counter();ticks=0
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  task=regs[15]>>12==0x18
  if task and pc==0x65606:active=False
  if task and pc==0x67120:active=True;ticks+=1
  if not active:continue
  owner=next((n for a,b,n in funcs if pc is not None and a<=pc<b),'other') if task else 'IRQ/OS'
  groups[owner]+=cost;pcs[pc]+=cost
  if task and pc==0x293d0:divargs[(regs[0],regs[1])]+=1
  if task and pc in (a for a,b,n in funcs):calls[hex(pc)]+=1
out={'scope':'32-field retained trace; costs within observed car-update spans, last call may be partial','tick_entries':ticks,'groups':dict(groups.most_common()),'calls':calls,'top_pcs':[{'pc':hex(p) if p is not None else None,'cost':c,'instruction':instructions.get(p)} for p,c in pcs.most_common(30)],'division_inputs':[{'d0':a,'d1':b,'count':n} for (a,b),n in divargs.most_common()]}
(r/'manifest/step5-tick-costs.json').write_text(json.dumps(out,indent=2)+'\n');print(out['tick_entries'],out['groups'],out['calls'])
