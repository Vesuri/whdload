import sys,json,re
from pathlib import Path
def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
def word(x):return (x+32768)%65536-32768
def project(v,t):
 sy,cy,sp,cp=t;speed=word((v>>1)+v);along=word(speed*cp>>14);return word(along*sy>>14)
for name in sys.argv[1:]:
 p=Path('tmp/prof')/name;pending=None;checks=0;backward=[];outputs=[]
 for tag,s in re.findall(r'^(PIN|POUT) ([-0-9 ]+)$',(p/'events.log').read_text(),re.M):
  row=list(map(int,s.split()))
  if tag=='PIN':pending=row;continue
  assert pending is not None
  f,pos,v,u,integer_carry,current,previous,fine,n,rem,speed,*trigs=pending
  assert v==project(speed,trigs),(name,pending)
  qnew=0 if not rem else word(project(speed+(1 if rem>0 else -1),trigs)-v)*abs(rem)*8192
  combined=(8*((8+n)*v-(8-n)*u)+integer_carry)*512+((8+n)*qnew-(8-n)*previous)//16+fine
  delta=trunc(combined,65536);qcarry=combined-delta*65536
  expected=(pos+delta,0,qnew,qcarry)
  got=(row[1],row[4],row[5],row[7]);assert got==expected,(name,pending,row,expected)
  checks+=1
  if row[1]<pos:backward.append((pending,row))
  outputs.append(row);pending=None
 assert not pending and checks and not backward,(name,backward)
 assert outputs[-1][9:11]==[0,0] and outputs[-1][5:7]==[0,0]
 assert outputs[-1][1]==outputs[-2][1]
 result=dict(passed=True,axis_updates=checks,backward_updates=0,stopped_velocity_carry=0,stopped_projection=0,final_position_held=True)
 (p/'projection-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result)
