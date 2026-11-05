"""Straight-course Normal/A2500/A4000 automatic drivetrain, decoded from F0D0..F7D4.

Car is a private bytearray; parameter reads are supplied from immutable RAM.
Caller owns contact flags, slope force, terrain/skid effects and input policy.
"""
import struct
from native_contact_response import word,trunc

def step(car,carry,param,read,input_byte=1,analog=0,hz=50):
    assert hz in (10,20,50)
    duration=lambda n:(n*hz+19)//20 if hz==50 else n
    car=bytearray(car);carry=dict(carry)
    w=lambda o:struct.unpack_from('>H',car,o)[0]
    sw=lambda o:word(w(o))
    def put(o,v):struct.pack_into('>H',car,o,v&65535)
    pb=lambda o:read(param+o,'B')
    pw=lambda o:read(param+o,'H')
    def approach(offset,target):
        current=sw(offset);target=word(target)
        if current==target:put(offset,target);carry['gear']=0;return
        sign=1 if target>current else -1
        if hz==50:
            numerator=12*sign+carry['gear'];delta=trunc(numerator,5);carry['gear']=numerator-delta*5
        else:delta=(12 if hz==10 else 6)*sign;carry['gear']=0
        result=current+delta
        if (result-target)*sign>=0:result=target;carry['gear']=0
        put(offset,result)
    if car[0xc6]:car[0xc6]-=1
    put(0x28,w(0x2c)-w(0x2e));put(0x2e,w(0x2c));put(0x24,w(0x22))
    shift=0
    if car[0xcc] or car[0xca]:
        if car[0xbe] and not car[0xca] and car[0xc0]:
            if w(0x22)>pw(0xa):shift=1
            elif w(0x22)<pw(8):shift=-1
    elif input_byte&16:shift=1
    elif input_byte&32:shift=-1
    if shift>0 and car[0xbe]!=pb(0) or shift<0 and car[0xbe]>1:
        car[0xbe]+=shift;car[0xca]=1;car[0xcb]=hz+hz//2
        put(0x3a,pw(0x1c+4*car[0xbe]));put(0x3c,pw(0x1e+4*car[0xbe]))
    if car[0xca]:
        if w(0x34)==w(0x3a):
            if w(0x38)==w(0x3c):
                car[0xca]=0;put(0x30,pw(0xe+2*car[0xbe]));put(0x32,w(0x30)>>8)
            else:approach(0x38,w(0x3c))
        elif w(0x38)==pw(0x1e):approach(0x34,w(0x3a))
        else:approach(0x38,pw(0x1e))
    elif car[0xcb]:car[0xcb]-=1
    pre=bytes(car)
    speed=w(0x2a);rpm=w(0x22);drag=read(read(param+0x304,'I')+2*(speed>>10),'h');a=word(sw(0x1e)-drag)
    if rpm>pw(0xc):rpm=pw(0xc)-1;a=word(a-pw(4));branch='rev_limit'
    else:
        assert analog==0 and input_byte&3==1,'Only held digital throttle currently supported'
        car[0xbc]=0;car[0xbd]=1
        if car[0xca]:car[0xc6]=0;rpm=(rpm-(16 if hz==50 else 80 if hz==10 else 40))&65535;branch='clutch'
        elif not car[0xc0]:
            if rpm<pw(0xc) and speed<64000:a=word(a+768)
            branch='airborne_throttle'
        else:
            torque=pb(0x3a) if car[0xbe]<=1 and word(rpm)<2600 else pb(0x3b+(rpm>>7))
            if car[0xc6] and word(rpm)<5000:torque=(torque+pb(0x3a))//2
            a=word(a+(((torque*w(0x32))&65535)>>4));a=word(trunc(a*25,pw(2))>>1)
            if a>296:car[0xc6]=duration(5)
            branch='grounded_torque'
    if hz==50:
        n=2*a+carry['acceleration'];scaled=trunc(n,5);carry['acceleration']=n-scaled*5
    else:scaled=word(2*a) if hz==10 else a;carry['acceleration']=0
    new_speed=(speed+scaled)&65535 if scaled>=0 else max(0,speed+scaled)
    if scaled>=0 and speed>=32768 and (new_speed<32768 or new_speed>62720):new_speed=62720
    if car[0xc0]:
        if abs(word(w(0x2c)-new_speed))>5120:new_speed=(speed+w(0x2c))//2;car[0xc6]=duration(5)
        put(0x2c,new_speed)
    put(0x2a,new_speed)
    rpm=max(pw(6),rpm if car[0xca] else (new_speed*w(0x30))>>16);put(0x22,rpm)
    if car[0xc1] and sw(0x24)>word(rpm):
        if sw(0x24)-word(rpm)>2000:
            if word((pb(0x3a)*w(0x32))&65535)>12000:car[0xc6]=duration(30)
        elif word(rpm)-sw(0x24)>2000:car[0xc6]=duration(10);put(0x2c,w(0x2c)-1280)
    if hz==50:distance,carry['distance']=divmod(2*((w(0x2c)*1408)//15360)+carry['distance'],5)
    else:distance=(w(0x2c)*1408)//(7680 if hz==10 else 15360);carry['distance']=0
    return car,carry,dict(pre_engine=pre,nominal_acceleration=a,scaled_acceleration=scaled,branch=branch,distance=distance)
