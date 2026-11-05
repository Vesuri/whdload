#!/usr/bin/env python3
"""Same-native-state local body reprojection at20/50Hz; no modified dynamics."""
import json,hashlib
from pathlib import Path
from copy import deepcopy
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import plane,rotate,sine,word
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20'if phase=='nominal'else 'phase-'+phase+'-native20');b,read,param=seed(cap)
 refs={r['tick']:r for r in json.loads((root/('coupled-course20-baseline'+(''if phase=='nominal'else '-'+phase)+'.json')).read_text())['rows']}
 checked=0
 while b['contact']['entry'][0]<=310:
  tick=b['contact']['entry'][0];b,r=advance(b,20,read,param);v=summarize(b);ref=refs[tick]
  assert v['position']+[v['pitch'],v['speed']]==[ref[k]for k in ('x','y','z','pitch','speed')];checked+=1
  if tick not in (190,224,259,261,310):continue
  runs={}
  for hz in (20,50):
   state=deepcopy(b)
   if hz==50:
    for o in (0xc6,0xcb):state['car'][o]=(5*state['car'][o]+1)//2
   steps=[]
   for i in range(hz//10):
    state,rec=advance(state,hz,read,param);c=rec['contact'];out=c['output'];pitch=out['pitch'];sn,cs=sine(pitch),sine(pitch+256);m=[16384,0,0,0,cs,-sn,0,sn,cs];wheels=[]
    for w,(q,end,su) in enumerate(zip(c['selected'],out['wheels'],out['suspensions'])):
     x,z=((-960,1984),(960,1984),(960,-1984),(-960,-1984))[w]
     rebuilt=[a+d for a,d in zip(out['position'],rotate([x,-384-su['extension'],z],m))]
     geo={k:q[k]for k in ('plane','normal_x','normal_y','normal_z')};geo.update({'origin_'+a:word(q['base_'+a]+q['node_'+a])for a in 'xyz'})
     before=plane(geo,end['position']);after=plane(geo,rebuilt)
     wheels.append(dict(wheel=w,branch=end['branch'],plane=q['plane'],resolved_clearance=before,rebuilt_clearance=after,reentered=end['branch']!='air'and before>=0 and after<0))
    steps.append(dict(ms=(i+1)*1000//hz,pitch=pitch,position=out['position'],wheels=wheels))
   reentry=[(s['ms'],w)for s in steps for w in s['wheels']if w['reentered']]
   runs[str(hz)]=dict(steps=steps,reentered_calls=len(reentry),worst_clearance=min((w['rebuilt_clearance']for _,w in reentry),default=0))
  cases.append(dict(phase=phase,seed_tick20=tick,initial=v,runs=runs))
 assert checked==309
report=dict(scope=__doc__,exact_native_seed_steps_per_phase=309,cases=cases,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(root/'contact-reprojection-matched.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:
 print(c['phase'],c['seed_tick20'],{h:{k:r[k]for k in ('reentered_calls','worst_clearance')}for h,r in c['runs'].items()})
