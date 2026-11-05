"""Exact straight, fully extended, contact-free predictor for current A4000."""
import re
from pathlib import Path
from native_contact_response import atan_native
_source=Path(__file__).resolve().parents[1]/'src/simulation_yaw.s'
text=_source.read_text().split('sim_yaw_atan_table:',1)[1]
TABLE=[int(v) for line in text.splitlines() if line.strip().startswith('dc.w ') for v in line.strip()[5:].split(',')]
assert len(TABLE)==257
def wrap(x,bits):return (x+(1<<(bits-1)))%(1<<bits)-(1<<(bits-1))
def atan_q8(x,y):
    flags=(1 if x<0 else 0)|(2 if y<0 else 0);x,y=abs(x),abs(y)
    if x==y:
        if not x:return 0
        q=32768
    else:
        if x>y:x,y=y,x;flags|=4
        index,f=divmod((x<<16)//y,256)
        q=TABLE[index]+((TABLE[index+1]-TABLE[index])*f+128)//256
        if flags&4:q=65536-q
    if flags&2:q=131072-q
    if flags&1:q=-q
    return q&0x3ffff
def axis(wheels):
    x=-(wheels[2][2]+wheels[3][2]-wheels[0][2]-wheels[1][2])
    y=wheels[2][1]+wheels[3][1]-wheels[0][1]-wheels[1][1]
    assert -32768<=x<32768 and -32768<=y<32768
    return x,y
def predict(wheels,velocities,vf,pf,carry):
    old=axis(wheels);assert old!=(0,0)
    down=[];nv=[];nf=[];np=[]
    for w,v in enumerate(velocities):
        a=21 if w<2 else 15
        d,p=divmod(10*v+2*vf[w]+7*a+pf[w],25)
        dv,f=divmod(2*a+vf[w],5)
        down.append(d);np.append(p);nv.append(v+dv);nf.append(f)
    final=(old[0],old[1]+sum(down[:2])-sum(down[2:]))
    assert final!=(0,0)
    baseline=atan_native(*old)*256
    delta=wrap(atan_q8(*final)-atan_q8(*old),18)
    base=baseline-65536+carry
    reference=wrap(2*base+5*delta,19);actual=wrap(2*base+2*delta,19)
    if max(abs(reference),abs(actual))<816:pitch=newcarry=0
    else:
        total=baseline+delta+carry+128;newcarry=total%256-128
        angle=(total>>8)&1023
        if angle>512 or angle==512 and final[0]<0:angle-=1024
        pitch=angle-256
    return dict(pitch=pitch,carry=newcarry,old_axis=old,final_axis=final,delta_q8=delta,downward=down,
                velocities=nv,velocity_fifths=nf,position_twentyfifths=np)
