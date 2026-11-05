import json,sys
from pathlib import Path
from drivetrain_model import advance
KEYS=['velocity','velocity_carry','rpm','rpm_carry','rpm_last','rpm_gear','gear','throttle']
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;d=json.loads((out/'drivetrain.json').read_text());start=None;rows=[]
 for r in d['rows']:
  if r['kind']=='ENTRY':start=None
  elif r['kind']=='FORCE':start=r
  elif r['kind']=='GEAR' and start and start['mask']==15 and start['road']==255 and start['auto']:
   s={k:start[k] for k in KEYS};expected,f=advance(s,start['interval'])
   assert (f['power'],f['rate'])==(start['power'],start['rate']),(name,start,f)
   assert all(expected[k]==r[k] for k in KEYS),(name,start,r,expected)
   fine=s;changes=[]
   for i in range(start['interval']):
    prev=fine;fine,_=advance(fine,1)
    if fine['gear']!=prev['gear']:changes.append(dict(field=i+1,gear=fine['gear'],velocity=fine['velocity'],carry=fine['velocity_carry'],rpm=fine['rpm']))
   rows.append(dict(field=start['field'],interval=start['interval'],start=s,whole=expected,one_field=fine,changes=changes))
 result=dict(passed=True,matched_updates=len(rows),scope='Flat held-input isolated drivetrain diagnostic; fine intervals do not model steering, contacts, position or control slew.',rows=rows)
 (out/'segment-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(name,'matched',len(rows))
 for r in rows:
  if r['changes'] or r['whole']['gear']!=r['start']['gear']:print(r)
