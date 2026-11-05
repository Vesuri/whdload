#!/usr/bin/env python3
"""Reproduce release gravity/extension, then attribute extension update order."""
import json
from fractions import Fraction as F
from pathlib import Path
p=Path('tmp/prof');out={}
for hz in (20,50):
 data=json.loads((p/f'first-release{hz}'/'takeoff-plane.json').read_text());rows=data['rows'];wheel_results=[]
 for w in range(4):
  selected={r['tick']:r for r in rows if r['wheel']==w and r['event']=='SELECT'}
  after={r['tick']:r for r in rows if r['wheel']==w and r['event']=='AFTER'}
  gravity={r['tick'] for r in rows if r['wheel']==w and r['event']=='GRAVITY'}
  positive=[];acc=21 if w<2 else 15;previous_rate=0;candidate_extension=None;carry=0
  for tick,r in sorted(after.items()):
   s=selected[tick]
   if tick in gravity:
    old=F(s['velocity'])+(F(s['velocity_fraction'],5) if hz==50 else 0)
    new=F(r['velocity'])+(F(r['velocity_fraction'],5) if hz==50 else 0)
    assert new-old==F(acc*20,hz)
   if r['clearance']<=0:previous_rate=0;candidate_extension=None;carry=0;continue
   rate=min(r['clearance'],192)
   if hz==20:expected=min(384,r['extension']+rate)
   else:expected=min(384,r['extension']+(2*rate+r['extension_fraction'])//5)
   if tick+1 in selected:assert selected[tick+1]['extension']==expected,(hz,w,tick,expected,selected[tick+1]['extension'])
   if candidate_extension is None:candidate_extension=r['extension']
   if hz==50:
    # For r(t) linear, reference20 right endpoint sum minus50 sum is
    # (1-.4)/2 * (r_end-r_start), hence .3 * delta per50 update.
    numerator=4*rate+3*(rate-previous_rate)+carry
    delta,carry=divmod(max(0,numerator),10)
    candidate_extension=min(384,candidate_extension+delta)
    if candidate_extension==384:carry=0
   positive.append(dict(tick=tick,rate=rate,actual_after=expected,ordered_on_recorded_clearance=candidate_extension if hz==50 else None,velocity=str(F(r['velocity'])+(F(r['velocity_fraction'],5) if hz==50 else 0))))
   previous_rate=rate
  wheel_results.append(dict(wheel=w,first_gravity=min(gravity)/hz,first_gravity_tick=min(gravity),rows=positive))
 out[str(hz)]=dict(wheels=wheel_results,plane_checks=len(data['plane_checks']))
# Independent identity for a linearly increasing rate across100ms: two20Hz
# increments versus five50Hz increments with the analytical endpoint term.
identities=0
for start in range(0,100,7):
 for slope in range(0,40,3):
  native=sum(F(start)+slope*t for t in (1,2));prev=F(start);fine=F(0)
  for k in range(1,6):
   rate=F(start)+slope*F(2*k,5);fine+=F(2,5)*rate+F(3,10)*(rate-prev);prev=rate
  assert fine==native;identities+=1
out['linear_rate_identities']=identities
out['scope']='All observed gravity increments and positive-clearance extension recurrences reproduced. Ordered extension is a recorded-clearance counterfactual only, not a runtime result. Formula is derived for linear clearance and requires contact/limit treatment and replay ownership before integration.'
(p/'first-release-model.json').write_text(json.dumps(out,indent=2)+'\n')
for hz,r in out.items():
 if hz not in ('20','50'):continue
 print(hz,'plane checks',r['plane_checks'])
 for w in (0,2):
  a=r['wheels'][w];sample=next(x for x in a['rows'] if x['tick']==round(11.4*int(hz)))
  print(w,'release',a['first_gravity'],'at11.4',sample)
print('linear-rate identities',identities)
