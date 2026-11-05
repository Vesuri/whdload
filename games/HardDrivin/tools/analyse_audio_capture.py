import json,re

def analyse(out,reply,a):
 if a.contact:
  contact_rows=[list(map(int,v.split())) for v in re.findall(r'^CONTACT ([-0-9 ]+)$',reply,re.M)]
  (out/'contacts.json').write_text(json.dumps(dict(columns=['site','field','step','mask','fall_velocity','velocity','gap0','gap1','gap2','gap3','object'],rows=contact_rows),indent=2)+'\n')
 events=[dict(kind=k,values=list(map(int,v.split()))) for k,v in re.findall(r'^(EVENT|REQUEST|START|ENGINE) ((?:\d+ ?)+)$',reply,re.M)]
 fields,steps=map(int,re.search(r'^END (\d+) (\d+)$',reply,re.M).groups());assert steps==a.steps if a.steps else fields==a.fields
 if a.gate:
  visits=[];before=None;mask=None;fall_velocity=0;bypasses=0;last_state=[0,0,0,0,0];last_impact=None;impact_step=None
  for tag,raw in re.findall(r'^(BEFORE|AFTER|CONTACT|IMPACT) ([-0-9 ]+)$',reply,re.M):
   v=list(map(int,raw.split()))
   if tag=='IMPACT':
    last_impact=v[0];impact_step=v[2];continue
   if tag=='CONTACT':
    if v[0]==0xcb0a:mask=v[3]
    if v[0]==0xcc80:fall_velocity=v[4]
    continue
   if tag=='BEFORE':assert before is None;before=v;continue
   if before is None and a.gate_kind in ('contact','landing','object'):
    # CD58 is also the native branch target for masks other than 3.
    if a.gate_kind=='contact':assert mask is not None and mask!=3,(mask,v)
    if a.gate_kind=='object':assert last_impact==0xbcf2,(last_impact,v)
    # CC8A also receives no-sound and hard-landing branches.
    assert v[2:7]==last_state,(v,last_state)
    bypasses+=1
    continue
   last_state=v[2:7]
   assert before is not None
   now,step,last,seen,req,emit,valid,active=before[:8]
   if active:
    afterwall,afterstep,newlast,newseen,newreq,newemit,newvalid,newactive=v[:8]
    assert afterstep==step and newseen==step and newreq==req+1 and newactive==active
    outcome=newemit-emit;assert outcome in (0,1)
    # VBL can fall between the entry stop, clock sample, and return stop.
    gap=(step-seen)&0xffffffff;span=(afterwall-now)&0xffffffff;assert span<=2
    possible=[]
    for tick in range(span+1):
     clock=(now+tick)&0xffffffff
     landing=a.gate_kind=='landing' and fall_velocity!=0
     if a.gate_kind=='object':
      obj,oldobj,projection=before[8:]
      assert v[8:]==[obj,obj,projection]
      landing=obj!=oldobj or projection!=0
     due=landing or not valid or gap>1 or (gap==1 and ((clock-last)&0xffffffff)>=8)
     expected_last=(clock if landing or not valid or gap>1 else (clock-((clock-last)&7))&0xffffffff) if due else last
     if int(due)==outcome and newlast==expected_last:possible.append(clock)
    assert possible and newvalid==(255 if outcome else valid),(before,v)
    visits.append(dict(step=step,observed_step=impact_step if a.gate_kind=='object' else None,before=now,after=afterwall,emitted=bool(outcome),gap=gap,fall_velocity=fall_velocity if a.gate_kind=='landing' else None))
   else:assert v[2:7]==before[2:7]
   before=None
  assert before is None and visits
  (out/'gate-check.json').write_text(json.dumps(dict(passed=True,bypasses=bypasses,visits=visits,emitted=sum(x['emitted'] for x in visits)),indent=2)+'\n')
 counts={k:sum(e['kind']==k for e in events) for k in ['EVENT','REQUEST','START','ENGINE']}
 report=dict(profile=a.profile,fields=fields,physics_returns=steps,counts=counts,events=events)
 (out/'audio.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='events'},flush=True)
