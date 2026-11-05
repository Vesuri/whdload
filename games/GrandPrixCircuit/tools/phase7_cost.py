import sys,re,json,os,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from gpc_report import regions
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());d=(p/'before.bin').read_bytes();os.environ['SLAVE']=str((p/'slave.slave').resolve());rr={n:(lo,hi) for lo,hi,n,o in regions(d,m['base'])};s=(p/'slave.slave.lst').read_text(encoding='latin1')
def sym(n):return rr['slave'][0]+int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)$',s,re.M)[1],16)
a=sym('render_pose_latch');b=sym('render_fraction');start=sym('sim_latch_enter');prepare=sym('render_subunit');h=m['code_base'];cost=total=0;frames=0;last=None;intervals=[];ticks=[];steps=0;last_steps=None;prepare_calls=0
t=barto.load(p/'trace.bin')
for f in t.fields:
 for pc,c,r in t.instructions(f):
  total+=c
  if pc is not None and a<=pc<b:cost+=c
  if pc==h+0x7754:steps+=1
  if pc==prepare:prepare_calls+=1
  if pc==start:
   frames+=1
   if last_steps is not None:ticks.append(steps-last_steps)
   last_steps=steps
   if last is not None:intervals.append(f.index-last)
   last=f.index
result=dict(fields=len(t.fields),helper_cycles=cost,total_cycles=total,helper_percent=100*cost/total,render_latches=frames,prepare_calls=prepare_calls,draw_intervals_fields=intervals,physics_steps_between_draws=ticks)
print(json.dumps(result,indent=2));(p/'phase7-cost.json').write_text(json.dumps(result,indent=2)+'\n')
