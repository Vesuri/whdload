#!/usr/bin/env python3
"""Audit resolved-wheel to next rigid-body projection, without changing physics.

Clearances use the SAME selected plane on both sides, not a new terrain query.
The exact world-vector split separates rigid basis fitting from suspension lift.
"""
import json,hashlib
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import plane,rotate,sine,word
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 suffix='' if phase=='nominal' else '-'+phase
 for hz in (20,50):
  name=('natural-crest20' if phase=='nominal' else 'phase-'+phase+'-native20') if hz==20 else ('crest-d9e7903' if phase=='nominal' else 'phase-'+phase+'-d9')
  b,read,param=seed(root/name)
  reference=json.loads((root/('coupled-course'+('20' if hz==20 else '')+'-baseline'+suffix+'.json')).read_text())['rows']
  checked=0;rows=[]
  for ref in reference:
   tick=b['contact']['entry'][0];assert tick==ref['tick']
   b,rec=advance(b,hz,read,param);v=summarize(b);c=rec['contact'];out=c['output'];e=c['entry']
   observed=dict(tick=tick,**dict(zip(('x','y','z'),v['position'])),pitch=v['pitch'],distance=rec['engine']['distance'],**{k:v[k]for k in ('speed','target','rpm','gear','clutch','flags')},carry=b['carry'])
   assert observed==ref,(phase,hz,tick,observed,ref);checked+=1
   pitch=out['pitch'];sn,cs=sine(pitch),sine(pitch+256);m=[16384,0,0,0,cs,-sn,0,sn,cs]
   for w,(q,end,su) in enumerate(zip(c['selected'],out['wheels'],out['suspensions'])):
    x,z=((-960,1984),(960,1984),(960,-1984),(-960,-1984))[w]
    resolved=end['position'];lift=rotate([0,384+su['returned'],0],e[4:13])
    basis=[a+d for a,d in zip(resolved,lift)]
    fitted=[a+d for a,d in zip(out['position'],rotate([x,0,z],m))]
    # Rotate each complete local vertex: separately rounded rotations need not add.
    rebuilt=[a+d for a,d in zip(out['position'],rotate([x,-384-su['extension'],z],m))]
    fitting=[a-d for a,d in zip(fitted,basis)]
    lift_effect=[a-d+old for a,d,old in zip(rebuilt,fitted,lift)]
    delta=[a-d for a,d in zip(rebuilt,resolved)]
    assert [a+d for a,d in zip(fitting,lift_effect)]==delta
    geo={k:q[k] for k in ('plane','normal_x','normal_y','normal_z')};geo.update({'origin_'+a:word(q['base_'+a]+q['node_'+a])for a in 'xyz'})
    before=plane(geo,resolved);after=plane(geo,rebuilt)
    rows.append(dict(tick=tick,time_ms=tick*1000//hz,wheel=w,plane=q['plane'],branch=end['branch'],pitch_before=e[2],pitch_after=pitch,extension_before=e[13+w],extension_after=su['extension'],returned=su['returned'],resolved_clearance=before,rebuilt_clearance=after,stored_clearance=end['clearance'],resolved=resolved,rebuilt=rebuilt,delta=delta,basis_fit=fitting,suspension_reprojection=lift_effect))
  contacts=[r for r in rows if r['branch']!='air'];reentered=[r for r in contacts if r['resolved_clearance']>=0 and r['rebuilt_clearance']<0]
  summary=dict(contact_calls=len(contacts),reentered_calls=len(reentered),reentered_ticks=len({r['tick']for r in reentered}),first_reentry=reentered[0]if reentered else None,worst_reentry=min(reentered,key=lambda r:r['rebuilt_clearance'])if reentered else None)
  cases.append(dict(phase=phase,hz=hz,exact_reported_baseline_steps=checked,summary=summary,rows=rows))
report=dict(scope=__doc__,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases)
(root/'contact-reprojection-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:print(c['phase'],c['hz'],c['exact_reported_baseline_steps'],json.dumps(c['summary']))
