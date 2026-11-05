from pathlib import Path
import json,re,sys
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1]
for name in sys.argv[1:]:
 p=r/'tmp/step5'/name;j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16);listing=Path(j['slave']).with_name('fine.list').read_text();syms={n:probe+int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
 t=barto.load(p/'detail.bin');loops=[];cur=None;active=None;cycles=0
 for f in t.fields:
  for pc,cost,regs in t.instructions(f):
   if active and regs[15]==active['sp']+4:
    if cur is not None:cur['roots'].append(cycles-active['start'])
    active=None
   if pc==0x65174:
    if cur is not None:loops.append(cur)
    cur={'roots':[],'seed_calls':0}
   if pc==syms['FF1SquareRootU64_000']:active={'sp':regs[15],'start':cycles}
   if pc==syms['FF1C4SeededRoot'] and cur is not None:cur['seed_calls']+=1
   cycles+=cost
 loops=loops[1:19];n=len(loops);total=sum(sum(x['roots']) for x in loops);calls=sum(len(x['roots']) for x in loops)
 out={'complete_updates':n,'root_calls':calls,'root_cycles_per_update':total/n,'cycles_per_call':total/calls,'seed_calls':sum(x['seed_calls'] for x in loops),'per_update':loops}
 (p/'root-cost.json').write_text(json.dumps(out,indent=2)+'\n');print(name,{k:v for k,v in out.items() if k!='per_update'})
