import sys,re,os,json,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from gpc_report import regions
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());os.environ['SLAVE']=str(p/'slave.slave');sb=next(lo for lo,hi,n,o in regions((p/'before.bin').read_bytes(),m['base']) if n=='slave');s=(p/'slave.slave.lst').read_text(encoding='latin1');names=['render_pose_latch','render_subunit','render_row_map','render_main_pose','render_mirror_pose','render_mirror_step','render_horizon_pose','render_scenery_pose','render_car_depth','render_car_y','render_car_near_y','render_mirror_car_y','render_angle','render_angle_integer','render_fraction'];sy=[(sb+int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)$',s,re.M)[1],16),n) for n in names];sy.sort();cost=collections.Counter();calls=collections.Counter();pcs=collections.Counter();counts=collections.Counter();t=barto.load(p/'trace.bin')
for f in t.fields:
 for pc,c,r in t.instructions(f):
  if pc is None or not sy[0][0]<=pc<sy[-1][0]:continue
  for (a,n),(b,_) in zip(sy,sy[1:]):
   if a<=pc<b:cost[n]+=c;calls[n]+=pc==a;break
  pcs[pc-sb]+=c;counts[pc-sb]+=1
print(dict(cost));print(dict(calls))
print([(hex(a),c,counts[a]) for a,c in pcs.most_common(25)])
