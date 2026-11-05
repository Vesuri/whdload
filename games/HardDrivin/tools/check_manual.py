import json,sys
from pathlib import Path
from audit_forward_force import word
from dissipation_model import trunc
T=[(0,800),(7,800),(9,750),(10,600),(10,450)]
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;rows=json.loads((out/'manual.json').read_text())['rows'];entry=None;before=None;shift=False;checks=neutral=deferred=0;changes=[];outers=set()
 for r in rows:
  if r['kind']=='ENTER':assert entry is None;entry=r;continue
  if r['kind']=='MANUAL':
   assert entry is not None and before is None
   n=1 if entry['active']==1 else entry['fields'];gear=entry['gear'];old=entry['rpm']
   if gear and r['mask']:
    num,den=T[gear];target=word(trunc(word(trunc(r['velocity']*140,500))*den,num))
   else:target=word(trunc(entry['throttle']*8000,100));neutral+=1
   diff=word(target-old);carry=entry['rpm_carry'] if entry['rpm_last']==old and entry['rpm_gear']==gear else 0
   numerator=(450 if diff>=0 else -450)*n+carry;delta=trunc(numerator,8);carry=numerator-delta*8
   if not diff or (diff>0 and diff<=delta) or (diff<0 and diff>=delta):delta=diff;carry=0
   value=word(old+delta)
   if value>=6500:carry=0
   value=max(0,min(6500,value))
   assert (r['rpm'],r['rpm_carry'])==(value,carry),(name,entry,r,target,value,carry)
   before=r;shift=False;continue
  if r['kind']=='SHIFT':assert before is not None and not shift;shift=True;continue
  assert r['kind']=='AFTER' and entry is not None and before is not None
  allow=before['active']!=1 or before['fields']==before['remaining'];req=before['joystick'] or before['request'];gear=before['gear'];rpm=before['rpm']
  if allow and req:
   assert shift and before['outer'] not in outers,(before,r,shift)
   outers.add(before['outer']);new=0 if req==5 else req
   assert 0<=new<=4
   if new:
    num,den=T[gear];nn,nd=T[new];target=word(trunc(word(trunc(rpm*num,den))*nd,nn))
    rpm=word(target+rpm)//2 if target>rpm else target
   assert r['request']==r['joystick']==0
   changes.append(dict(control=before['controls'],old=gear,new=new,rpm_before=before['rpm'],rpm_after=rpm));gear=new
  else:
   assert not shift,(before,r)
   assert (r['request'],r['joystick'])==(before['request'],before['joystick'])
   deferred+=not allow
  assert (r['gear'],r['rpm'])==(gear,rpm),(before,r,gear,rpm)
  checks+=1;entry=before=None
 assert entry is None and before is None and checks and neutral and deferred
 result=dict(passed=True,engine_updates=checks,neutral_rpm_updates=neutral,deferred_manual_visits=deferred,changes=changes)
 if all('skid' in r for r in rows):result['skid_engine_updates']=sum(r['kind']=='AFTER' and bool(r['skid']) for r in rows)
 (out/'manual-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result)
