import json,re,sys
from pathlib import Path
def trunc(x,d):return abs(x)//d*(-1 if x<0 else 1)
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;pending=None;pin=None;count=0;skipped=0
 for tag,vals in re.findall(r'^(FIXED|PIN|POUT) ([-0-9 ]+)$',(out/'events.log').read_text(),re.M):
  row=list(map(int,vals.split()))
  if tag=='FIXED':
   assert pending is None
   assert len(row)==18 and row[1]>1,row
   assert row[2:10]==row[10:18],row
   pending=row
  elif tag=='PIN' and pending:
   pin=row;assert row[0]==pending[0] and row[8]==pending[1]
  elif tag=='POUT' and pending:
   assert pin is not None
   f,pos,v,u,integer,current,previous,fine,n,*_=pin
   assert v==u and current==previous,(pin,row)
   # Repeat exactly n single-field position integrations at this fixed vector.
   for i in range(n):
    numerator=16*v*512+integer*512+current//8+fine
    delta=trunc(numerator,65536);fine=numerator-delta*65536;pos+=delta;integer=0
   assert (row[1],row[4],row[7])==(pos,0,fine),(pin,row,pos,fine)
   count+=1;skipped+=n;pending=None;pin=None
 assert count and pending is None
 result=dict(passed=True,bulk_updates=count,skipped_fields=skipped,engine_inputs_identical=True,position_matches_repeated_fields=True)
 (out/'settled-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result)
