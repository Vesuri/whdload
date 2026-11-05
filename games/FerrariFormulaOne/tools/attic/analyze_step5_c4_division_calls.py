from pathlib import Path
import json,re,sys,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1];j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16)
listing=Path(j['slave']).with_name('fine.list').read_text();sym={n:probe+int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
t=barto.load(p/'detail.bin');cur=None;loops=[];prev=None;native_caller=None;active=None;cycles=0
for f in t.fields:
 for pc,cost,regs in t.instructions(f):
  if active and regs[15]==active['sp']+4:
   active['cycles']=cycles-active.pop('start');active=None
  if pc==0x65174:
   if cur is not None:loops.append(cur)
   cur=[]
  if pc==0x293d0:native_caller=prev
  if pc==sym['FF1Divide000'] and cur is not None:
   caller=native_caller if prev==0x293d0 else prev
   active={'caller':caller,'sp':regs[15],'start':cycles,'d0':regs[0],'d1':regs[1]};cur.append(active)
  prev=pc;cycles+=cost
loops=loops[1:19];sites={}
for row in [x for loop in loops for x in loop]:
 key=hex(row['caller']);v=sites.setdefault(key,{'calls':0,'cycles':0,'divisors':{},'native':row['caller']<0x100000})
 v['calls']+=1;v['cycles']+=row.get('cycles',0);k=str(row['d1']);v['divisors'][k]=v['divisors'].get(k,0)+1
out={'updates':len(loops),'sites':dict(sorted(sites.items(),key=lambda kv:-kv[1]['calls']))}
(p/'division-calls.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
