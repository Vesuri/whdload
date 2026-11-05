from pathlib import Path
import sys,re,json,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1];t=barto.load(p/'detail.bin');loop=-1;prev=0;active=None;rows=collections.defaultdict(collections.Counter)
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==0x65174:loop+=1
  if not 1<=loop<=20:prev=pc;continue
  if pc in (0x29500,0x24fe0,0x25000,0x6977a):active=(pc,prev)
  if active:
   entry,caller=active
   if pc is not None and ((entry==0x29500 and 0x29500<=pc<=0x29540) or (entry in (0x24fe0,0x25000) and entry<=pc<entry+32) or (entry==0x6977a and 0x6977a<=pc<0x6988c)):
    rows[(entry,caller)]['cycles']+=cost
    if pc==entry:rows[(entry,caller)]['calls']+=1
   if pc in (0x29540,0x24ffe,0x2501e,0x697e4,0x6988a):active=None
  prev=pc
out=[dict(entry=hex(k[0]),caller=hex(k[1]),**v) for k,v in sorted(rows.items(),key=lambda x:-x[1]['cycles'])];(p/'hotspots.json').write_text(json.dumps(out,indent=2)+'\n')
for x in out[:25]:print(x)
