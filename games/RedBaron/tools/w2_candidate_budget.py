"""Bound remaining W2 work using only complete 3D passes in retained captures."""
import json,sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,'tools')
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
p=Path(sys.argv[1]); costs=json.loads((p/'steady-costs.json').read_text());state=json.loads((p/'step8.json').read_text());sim=state['sim'];low,high=costs['irq_stack']
completed=[]; frame_costs=[]
for f in sorted(p.glob('steady-*/trace.bin')):
 active=None; frame_main=None
 trace=barto.load(f)
 for field in trace.fields:
  for pc,cycles,regs in trace.instructions(field):
   if pc==sim+0x2c552:
    if frame_main is not None:frame_costs.append(frame_main)
    frame_main=0;active=(Counter(),Counter())
   if frame_main is not None and pc!=0x7fffffff and not low<=regs[15]<high:frame_main+=cycles
   if active is None:continue
   if pc!=0x7fffffff and not low<=regs[15]<high:
    active[0][pc-sim]+=cycles;active[1][pc-sim]+=1
   if pc==sim+0x2c806:
    completed.append(active);active=None
n=len(completed);assert n>0
hist=sum((x[0] for x in completed),Counter());counts=sum((x[1] for x in completed),Counter())
ranges={'G1_wrapper':(0x38e9c,0x38eec),'G5_face_self':(0x3b41a,0x3b5e8),'G6_setup_self':(0x3b0f6,0x3b1fa),'G8_lod_self':(0x3a518,0x3a8b4),'G8_object_self':(0x3a902,0x3aa4c),'G9_clear_total':(0x3a8b4,0x3a902)}
result={'complete_frame_intervals':len(frame_costs),'mean_frame_main_cycles':sum(frame_costs)/len(frame_costs),'complete_3d_passes':n,'mean_main_cycles':sum(hist.values())/n,'ranges':{k:{'calls_per_pass':counts[a]/n,'own_cycles_per_pass':sum(v for pc,v in hist.items() if a<=pc<b)/n} for k,(a,b) in ranges.items()},'16bit_cache_calls_per_pass':counts[0x3abe2]/n,'16bit_transform_calls_per_pass':counts[0x3aede]/n,'G6_bsr_calls_per_pass':sum(counts[a] for a in [0x3b128,0x3b136,0x3b148,0x3b156,0x3b172,0x3b180,0x3b18e,0x3b1a0,0x3b1ae,0x3b1bc,0x3b1ce,0x3b1dc,0x3b1ea])/n}
(p/'candidate-budget.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
