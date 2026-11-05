"""Complete entry-to-return costs, excluding interrupt execution and partial calls."""
import argparse,json,struct
from pathlib import Path
from functools import lru_cache
import barto_mmap as bm
from harddrivin_report import contexts
p=argparse.ArgumentParser();p.add_argument('names',nargs='+');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof'
phases={0x7c32:'controls',0x108a2:'recovery',0xd960:'camera',0xd40e:'traffic',0xe49a:'scene_e49a',0xb0d6:'scene_b0d6',0xcda4:'physics',0xe706:'background',0x10008:'scene_drawing',0xeb22:'cockpit',0x10020:'score',0x10b08:'replay',0x740:'wait',0x750:'submit',0x329a:'polygon_filler'}
for name in a.names:
 out=root/name;meta=json.loads((out/'metadata.json').read_text());base=meta['layout']['code_base'];trace=bm.load(out/'trace.bin');metrics=json.loads((out/'window-metrics.json').read_text());factor=metrics['cycle_unit']/(metrics['trace_clock']*64)*1000
 banks=[(0,(out/'before-chip.bin').read_bytes()),(0xc00000,(out/'before-slow.bin').read_bytes())]
 @lru_cache(maxsize=100000)
 def word(pc):
  for start,b in banks:
   if start<=pc<start+len(b)-1:return struct.unpack_from('>H',b,pc-start)[0]
  return None
 ranges=contexts(trace,trace.fields)
 entry_sp=next(regs[15] for f in trace.fields for pc,c,regs in trace.instructions(f) if pc==base+0xcda4)
 main=next((lo,hi) for lo,hi in ranges if lo<=entry_sp<hi)
 active=[];finished={n:[] for n in phases.values()};polygon_counts={n:[] for n in phases.values()};closures=[]
 for f in trace.fields:
  for pc,c,regs in trace.instructions(f):
   sp=regs[15]
   if pc==0x7fffffff or not main[0]<=sp<main[1]:continue
   if pc is not None:
    continuing=[]
    for row in active:
     if sp>row['sp']:
      finished[row['name']].append(row['cycles']);polygon_counts[row['name']].append(row['polygons'])
      if row['name']=='physics':closures.append(dict(field=f.index,pc=hex(pc-base),sp=hex(sp),entry_sp=hex(row['sp']),cycles=row['cycles']))
     else:continuing.append(row)
    active=continuing
    if pc==base+0x329a:
     for row in active:row['polygons']+=1
    if pc-base in phases:active.append(dict(name=phases[pc-base],sp=sp,cycles=0,polygons=0))
   for row in active:row['cycles']+=c
 result=dict(scope='Complete entry-to-return calls. Interrupts and calls crossing trace boundaries excluded. Nested phase costs overlap and must not be added.',phases={n:dict(calls=len(v),total_ms=sum(v)*factor,mean_ms=sum(v)/len(v)*factor if v else None,minimum_ms=min(v)*factor if v else None,maximum_ms=max(v)*factor if v else None) for n,v in finished.items()},incomplete_calls=active,physics_closures=closures,main_stack_context=main,polygon_calls_within_complete_phases={n:dict(total=sum(v),mean=sum(v)/len(v) if v else None) for n,v in polygon_counts.items()})
 assert all(x['pc']=='0x10f28' for x in closures),'physics call closed in the wrong execution context'
 assert result['phases']['physics']['calls']==metrics['physics_completed_calls']
 (out/'complete-phase-costs.json').write_text(json.dumps(result,indent=2)+'\n');print(name,json.dumps(result['phases'],indent=2))
