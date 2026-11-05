from pathlib import Path
import sys,collections,json,re,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5/optimized-detail-v6';listing=(r/'tmp/build/step5-math-v6/logic.list').read_text()
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
memory=(p/'end.bin').read_bytes();stub=struct.unpack_from('>I',memory,0x293d2)[0]-sym('FF1Divide020')
funcs=[(0x67120,0x68730,'car body'),(0x68730,0x69bac,'AI/contact helpers'),(0x6cd00,0x6d4cc,'engine force helpers'),(0x6d4cc,0x6dc38,'drag/RPM/gear'),(0x6dc38,0x6e2f6,'velocity/slip/tyre response'),(0x6e2f6,0x6ea3e,'engine curves'),(0x6ea3e,0x6ec94,'wear'),(0x6ec94,0x6ef20,'failure helpers'),(0x29500,0x29542,'remaining software multiply'),(0x24fe0,0x25020,'sin/cos'),(stub+sym('FF1Divide000'),stub+sym('FF1DivDone')+6,'fast division'),(stub+sym('FF1SquareRoot020'),stub+sym('FF1Squares'),'fast sqrt')]
trace=barto.load(p/'detail.bin');started=False;physics=False;current=collections.Counter();pcs=collections.Counter();complete=[];calls=collections.Counter();loop_calls=collections.Counter();entries={a:name for a,b,name in funcs}
for field in trace.fields:
 for pc,cost,regs in trace.instructions(field):
  task=regs[15]>>12==0x18
  if task and pc==0x65174:
   if started:complete.append({'costs':dict(current),'calls':dict(loop_calls)})
   started=True;physics=False;current=collections.Counter();loop_calls=collections.Counter()
  if not started:continue
  if task and pc==0x67120:physics=True
  if task and pc==0x65606:physics=False
  owner=next((name for a,b,name in funcs if pc is not None and a<=pc<b),'other physics') if task and physics else ('other main loop' if task else 'IRQ/OS')
  current[owner]+=cost
  if task and physics:pcs[pc]+=cost
  if task and physics and pc in entries:loop_calls[entries[pc]]+=1
sums=collections.Counter()
for loop in complete:sums.update(loop['costs'])
count=len(complete);out={'scope':'complete loops only from 32-field stock-68020 trace, optimized native integrator and gauge-free omission','complete_loops':count,'stub_base':hex(stub),'mean_cycles':sum(sums.values())/count,'groups_mean_cycles':{k:v/count for k,v in sums.most_common()},'loops':complete,'physics_top_pcs_including_partial_last_loop':[{'pc':hex(k),'cycles':v} for k,v in pcs.most_common(30)]}
(r/'manifest/step5-optimized-costs.json').write_text(json.dumps(out,indent=2)+'\n');print(count,'complete loops',out['mean_cycles'],'cycles/loop');print(out['groups_mean_cycles'])
