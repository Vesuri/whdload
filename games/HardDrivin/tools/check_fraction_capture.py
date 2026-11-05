import json,re,sys
from pathlib import Path
def trunc(x,d):return abs(x)//d*(-1 if x<0 else 1)
def word(x):return (x+32768)%65536-32768
def project(v,t):
 sy,cy,sp,cp=t;speed=word((v>>1)+v);along=word(speed*cp>>14);return word(along*sy>>14)
def correction(v,r,t):
 return 0 if not r else word(project(v+(1 if r>0 else -1),t)-project(v,t))*abs(r)*8192
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;pending=None;pin=None;count=0;skipped=0;rates=set();skid=False;skid_batches=0
 for tag,vals in re.findall(r'^(FRAC|PIN|POUT|MODE PIN) ([-0-9 ]+)$',(out/'events.log').read_text(),re.M):
  row=list(map(int,vals.split()))
  if tag=='MODE PIN':skid=bool(row[1]);continue
  if tag=='FRAC':
   assert pending is None and len(row)==19 and row[1]>=1 and row[2]!=0,row
   observed,saved=row[3:11],row[11:19]
   assert observed[1:]==saved[1:] and observed[0]&65535==saved[0]&65535,row
   n,rate=row[1:3];r0=word(saved[0]>>16);r2=word(observed[0]>>16);r1=r0+rate
   assert r2==r0+(n+1)*rate and -7<=r1<=7 and -7<=r2<=7 and r1*r2>=0,row
   pending=row
  elif tag=='PIN' and pending:
   pin=row;assert row[0]==pending[0] and row[8]==pending[1]
  elif tag=='POUT' and pending:
   assert pin is not None
   f,pos,v,u,integer,current,previous,fine,n,rem,speed,*trigs=pin
   rate=pending[2];r1=rem-n*rate
   assert 2<=abs(speed)<=21843 and v==u and current==previous,(pending,pin)
   if not skid:assert current==correction(speed,r1,trigs),(pending,pin)
   q=previous
   for i in range(n):
    qnext=q if skid else correction(speed,r1+(i+1)*rate,trigs)
    numerator=16*v*512+integer*512+(9*qnext-7*q)//16+fine
    delta=trunc(numerator,65536);fine=numerator-delta*65536;pos+=delta;integer=0;q=qnext
   assert (row[1],row[4],row[5],row[7])==(pos,0,q,fine),(pin,row,pos,q,fine)
   count+=1;skid_batches+=skid;skipped+=n;rates.add(rate);pending=None;pin=None
 assert count and pending is None
 result=dict(passed=True,bulk_updates=count,skid_batches=skid_batches,skipped_fields=skipped,rates=sorted(rates),other_engine_inputs_identical=True,position_matches_repeated_fields=True)
 (out/'fraction-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result)
