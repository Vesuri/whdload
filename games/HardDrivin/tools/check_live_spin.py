from pathlib import Path
import json
checks=0;reports=[]
for suffix in ['020','040','a500']:
 root=Path('tmp/prof/physics-handling-v2-'+suffix)
 rows=json.loads((root/'motion.json').read_text())['rows'];before=None;count=0;exits=0
 for row in rows:
  if row['kind']=='INPUT':before=row
  elif row['kind']=='INTEGRATED' and before:
   if before['skid']:
    phase=before['spin_carry'] if before['spin']==before['spin_last'] else 0
    n=before['interval'];v=before['spin']
    for _ in range((phase+n)//8):
     product=(v*9+32768)%65536-32768
     v=abs(product)//10*(-1 if product<0 else 1)
    assert row['spin']==v,(suffix,before,row,v)
    expected_phase=(phase+n)%8 if row['skid'] else 0
    assert row['spin_carry']==expected_phase,(suffix,before,row,expected_phase)
    assert v or not row['skid']
    exits+=not row['skid'];count+=1
   before=None
 assert count and exits>=2
 reports.append(dict(profile=suffix,checked_skid_returns=count,exits=exits));checks+=count
report=dict(passed=True,checks=checks,reports=reports,scope='Read-only running-game spin recurrence and phase checks on every captured pre-existing skid; includes actual road departures/contact. Does not replace full trajectory or skid-entry oracle.')
Path('tmp/live-spin-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
