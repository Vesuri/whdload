"""Diagnostic isolated drivetrain model; flat terrain and held inputs only."""
from audit_forward_force import force,word
from dissipation_model import update,trunc
TABLE=[(0,800),(7,800),(9,750),(10,600),(10,450)]
def convert(v,num,den):
 # Native $2950: MULS.W then DIVS.W. Quotient overflow leaves the
 # dividend register unchanged; callers consume its low word regardless of V.
 dividend=word(v)*word(num);divisor=word(den)
 assert divisor, 'Native DIVS divisor zero is outside this fixture'
 quotient=trunc(dividend,divisor) if divisor>0 else -trunc(dividend,-divisor)
 return word(dividend if not -32768<=quotient<=32767 else quotient)

def engine_speed(rpm,gear):
 num,den=TABLE[gear]
 return convert(convert(rpm,num,den),500,140)
def advance(s,n):
 s=dict(s);gear=s['gear'];num,den=TABLE[gear];old=s['velocity'];rpm=s['rpm']
 power=convert(convert(s['throttle'],450,100),den,num)&65535
 if abs(engine_speed(rpm,gear)-old)>10:power//=2
 f=force(old,power,True,False,False,False,0)
 v=update(old,f['rate'],n,s['velocity_carry'],old,f['drive'],f['drag'],0,0)
 s['velocity']=v['value'];s['velocity_carry']=v['carry']
 target=convert(convert(s['velocity'],140,500),den,num);diff=word(target-rpm)
 carry=s['rpm_carry'] if s['rpm_last']==rpm and s['rpm_gear']==gear else 0
 numerator=(450 if diff>=0 else -450)*n+carry;delta=trunc(numerator,8);carry=numerator-delta*8
 if not diff or (diff>0 and diff<=delta) or (diff<0 and diff>=delta):delta=diff;carry=0
 value=rpm+delta
 if value>=6500:carry=0
 value=max(0,min(6500,word(value)))
 s['rpm']=value;s['rpm_carry']=carry;s['rpm_last']=value;s['rpm_gear']=gear
 newgear=gear
 if value<2000 and gear>1:newgear-=1
 elif value>5200 and gear<4:newgear+=1
 if newgear!=gear:
  newnum,newden=TABLE[newgear];s['rpm']=convert(convert(value,num,den),newden,newnum);s['gear']=newgear
 return s,dict(power=power,rate=f['rate'])
