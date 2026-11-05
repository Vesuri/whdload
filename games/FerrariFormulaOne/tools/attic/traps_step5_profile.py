#!/usr/bin/env python3
# Count WHDLoad MOVE-from-SR privilege emulation traps per complete update and
# attribute them (and their handler cycles) to the trapping instruction.
from pathlib import Path
import sys,collections,json,re,struct,bisect
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];name=sys.argv[1];p=r/'tmp/step5'/name
build=Path(json.loads((p/'result.json').read_text())['slave']).parent
listing=(build/'fine.list').read_text()
syms=sorted((int(a,16),n) for n,a in re.findall(r'^([A-Za-z_][\w.]*)\s+00:([0-9A-F]{8})$',listing,re.M))
addrs=[a for a,_ in syms];symbol={n:a for a,n in syms}
probe=struct.unpack_from('>I',(p/'end.bin').read_bytes(),0x654e8)[0]-symbol['barrier']
def label(pc):
 if probe<=pc<probe+symbol['velocity_records']:return syms[bisect.bisect_right(addrs,pc-probe)-1][1]
 return 'native %06x'%pc
t=barto.load(p/'detail.bin')
# handler entry: first instruction of the vector-$20 path that reads the stacked PC
entry=int(sys.argv[2],16) if len(sys.argv)>2 else None
started=False;loops=[];cur=collections.Counter();cyc=collections.Counter();intrap=False;site=None;prev=None
hlo,hhi=(entry,int(sys.argv[3],16))
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if pc==0x65174:
   if started:loops.append((cur,cyc))
   started=True;cur=collections.Counter();cyc=collections.Counter()
  if not started or pc is None:continue
  inh=hlo<=pc<hhi
  if inh and not intrap:
   intrap=True;site=label(prev) if prev is not None else '?';cur[site]+=1
  if not inh:intrap=False;prev=pc
  if inh:cyc[site]+=cost
n=len(loops);c=collections.Counter();y=collections.Counter()
for a,b in loops:c.update(a);y.update(b)
print(n,'updates; traps/update',sum(c.values())/n,'handler cycles/update',sum(y.values())/n)
for k,v in c.most_common(40):print('%7.1f traps %8.0f cyc  %s'%(v/n,y[k]/n,k))
json.dump({'updates':n,'traps':{k:v/n for k,v in c.items()},'cycles':{k:v/n for k,v in y.items()}},open(p/'traps.json','w'),indent=1)
