from pathlib import Path
import sys,json,bisect,collections,statistics,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];probe=int(r['probe'],16);host=int(r['host'],16)
rows=sorted(json.loads((p/'addresses.json').read_text()),key=lambda x:x['actual']);keys=[x['actual'] for x in rows]
def canon(pc):
 if pc is None:return -1
 i=bisect.bisect_right(keys,pc)-1
 if i>=0 and pc<rows[i]['actual']+rows[i]['size']:return rows[i]['old']+pc-rows[i]['actual']
 return pc
labels=sorted((v,k) for k,v in sy.items());sk=[v for v,k in labels]
hlabels=sorted((v,k) for k,v in r['host_symbols'].items());hk=[v for v,k in hlabels]
def owner(pc):
 if pc is None:return 'STOP'
 if pc==0x7fffffff:return 'unattributed gap'
 if probe<=pc<probe+max(sk):return 'fine:'+labels[bisect.bisect_right(sk,pc-probe)-1][1]
 if host<=pc<host+max(hk):return 'host:'+hlabels[bisect.bisect_right(hk,pc-host)-1][1]
 return 'native:'+hex(canon(pc)&~0xff)
points=[('setup','B8Draw'),('beam wait','B8_65728'),('6b050','B8_65734'),('6b950','B8_6573a'),('road','B8_65748'),('optional scene','B8_65790'),('remaining scene/HUD','B8_657a6'),('final waits/publish','B8_65d6e')]
marks={probe+sy[v]:k for k,v in points};end=probe+sy['B8Frames']-2
trace=barto.load(p/'detail.bin');tot=collections.Counter();pcs=collections.Counter();draws=[];cur=None;stage=None;field_costs=[];startcost=0;running=0;entries=[];drawirq=collections.Counter()
for f in trace.fields:
 fc=0
 for pc,cost,regs in trace.instructions(f):
  irq=(regs[16]>>8)&7
  if pc==probe+sy['B8Draw']:
   assert cur is None
   cur={'cycles':0,'stages':collections.Counter(),'exclusive':collections.Counter(),'owners':collections.Counter(),'pcs':collections.Counter()};startcost=running;entries.append(running)
  if pc in marks and not irq:stage=marks[pc]
  key='gap' if pc==0x7fffffff else 'STOP' if pc is None else 'irq' if irq else 'draw' if cur is not None else 'outside draw'
  tot[key]+=cost;pcs[pc]+=cost;fc+=cost;running+=cost
  if cur is not None:
   cur['cycles']+=cost;cur['stages'][stage]+=cost
   cur['exclusive'][key]+=cost;cur['owners'][owner(pc)]+=cost;cur['pcs'][pc]+=cost
   if irq:drawirq[canon(pc)]+=cost
  if pc==end and cur is not None:
   draws.append(cur);cur=None;stage=None
 field_costs.append({'field':f.index,'header':f.cycles,'sum':fc,'idle':f.idle})
clock=14187580;n=len(draws);assert n>0
agg={k:sum((d[k] for d in draws),collections.Counter()) for k in ['stages','exclusive','owners','pcs']}
ms=lambda c:c/clock*1000
out={'complete_draws':n,'fields':len(trace.fields),'clock_hz':clock,'trace_seconds':running/clock,'field_accounting':field_costs,'field_costs_exact':all(x['header']==x['sum'] for x in field_costs),'all_phase_ms':{k:ms(v) for k,v in tot.items()},'draw_ms':[ms(d['cycles']) for d in draws],'mean_draw_ms':ms(sum(d['cycles'] for d in draws)/n),'draw_interval_ms':[ms(b-a) for a,b in zip(entries,entries[1:])],'stage_ms_per_draw':{k:ms(v/n) for k,v in agg['stages'].most_common()},'exclusive_ms_per_draw':{k:ms(v/n) for k,v in agg['exclusive'].most_common()},'owners_ms_per_draw':{k:ms(v/n) for k,v in agg['owners'].most_common(50)},'top_pcs':[{'actual':hex(k) if k is not None else None,'canonical':hex(canon(k)),'owner':owner(k),'ms_per_draw':ms(v/n)} for k,v in agg['pcs'].most_common(60)],'irq_pcs':[{'canonical':hex(k),'ms':ms(v)} for k,v in drawirq.most_common(20)]}
(p/'render-analysis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['top_pcs','irq_pcs','field_accounting']},indent=2))
