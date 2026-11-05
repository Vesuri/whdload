import json,sys
from pathlib import Path
def trunc(n,d):return abs(n)//abs(d)*(-1 if n*d<0 else 1)
def word(n):return (n+32768)%65536-32768
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;d=json.loads((out/'drivetrain.json').read_text());table=d['gear_table'];force=None;rpm=None;checks=0;shifts=[];neutral=0
 for r in d['rows']:
  if r['kind']=='ENTRY':force=None;rpm=None
  elif r['kind']=='FORCE':force=r
  elif r['kind']=='RPM':
   rpm=r
   if force is None:neutral+=1;continue
   gear=force['gear'];num,den=table[gear]
   assert gear and force['mask']
   target=word(trunc(word(trunc(r['velocity']*140,500))*den,num))
   old=force['rpm'];diff=word(target-old)
   carry=force['rpm_carry'] if force['rpm_last']==old and force['rpm_gear']==gear else 0
   numerator=(450 if diff>=0 else -450)*force['interval']+carry
   delta=trunc(numerator,8);rem=numerator-delta*8
   if diff==0 or (diff>0 and diff<=delta) or (diff<0 and diff>=delta):delta=diff;rem=0
   value=old+delta
   if value>=6500:rem=0
   value=max(0,min(6500,word(value)))
   assert (r['rpm'],r['rpm_carry'])==(value,rem),(name,force,r,target,value,rem)
   checks+=1
  elif r['kind']=='GEAR':
   assert rpm is not None
   gear=rpm['gear'];value=rpm['rpm'];newgear=gear
   if rpm['auto']:
    if value<2000 and gear>1:newgear-=1
    elif value>5200 and gear<4:newgear+=1
   if newgear!=gear:
    num,den=table[gear];newnum,newden=table[newgear]
    value=word(trunc(word(trunc(value*num,den))*newden,newnum))
   assert (r['gear'],r['rpm'])==(newgear,value),(name,rpm,r,newgear,value)
   if newgear!=gear:shifts.append(dict(force=force,before=rpm,after=r))
 result=dict(passed=True,engaged_rpm_updates=checks,neutral_rpm_updates=neutral,shifts=shifts,gear_table=table)
 (out/'drivetrain-check.json').write_text(json.dumps(result,indent=2)+'\n');print(name,checks,'RPM checks',len(shifts),'shifts')
 for s in shifts:print(s)
