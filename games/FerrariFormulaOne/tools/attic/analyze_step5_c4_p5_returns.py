from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1]
sites={0x671ec,0x67214,0x67222,0x6854c,0x6857c,0x685ac,0x67b58}
def collect(name):
 p=r/'tmp/step5'/name;t=barto.load(p/'detail.bin');loops=[];cur=None
 for f in t.fields:
  for pc,cost,regs in t.instructions(f):
   if pc==0x65174:
    if cur is not None:loops.append(cur)
    cur=[]
   if pc in sites and cur is not None:cur.append((pc,list(regs[:16])+[regs[16]&31]))
 return loops[1:19]
a=collect(sys.argv[1]);b=collect(sys.argv[2]);assert len(a)==len(b)
bad=[];counts={hex(pc):0 for pc in sites}
for step,(x,y) in enumerate(zip(a,b)):
 if len(x)!=len(y):bad.append({'step':step,'count_a':len(x),'count_b':len(y)});continue
 for i,(u,v) in enumerate(zip(x,y)):
  counts[hex(u[0])]+=1
  if u!=v:bad.append({'step':step,'call':i,'pc':hex(u[0]),'a':u[1],'b':v[1]})
out={'status':'passed' if not bad else 'failed','updates':len(a),'return_counts':counts,'scope':'All D0-D7/A0-A7 and XNZVC at the seven touched native continuations; matched complete omitted-drawing updates.','failures':bad[:20]}
(r/'manifest/step5-c4-p5-v1-returns.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));assert not bad
