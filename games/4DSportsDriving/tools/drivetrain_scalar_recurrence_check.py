#!/usr/bin/env python3
"""Reproduce acceleration and RPM from car inputs and original parameter tables."""
import json,struct,collections
from pathlib import Path
from native_contact_response import word,trunc
cap=Path('tmp/prof/drivetrain-feedback-inputs-d9');data=json.loads((cap/'drivetrain.json').read_text());r=data['records'];meta=json.loads((cap/'anchor.json').read_text());ram=(cap/'memory.bin').read_bytes()
def read(addr,fmt):return struct.unpack_from('>'+fmt,ram,addr-meta['memory_base'])[0]
branches=collections.Counter();rows=[];state=None;carry=None;distance_carry=None
for pre,ac,en,sy in zip(*(r[k] for k in ('PRE_ENGINE','ACCEL','ENGINE_END','SYNC'))):
    tick,param,input_byte,analog,*words=pre;car=struct.pack('>104H',*words)
    w=lambda o:struct.unpack_from('>H',car,o)[0]
    sw=lambda o:word(w(o))
    pb=lambda o:read(param+o,'B')
    pw=lambda o:read(param+o,'H')
    if state is None:state=dict(speed=w(0x2a),target=w(0x2c),rpm=w(0x22));carry=ac[3];distance_carry=r['DIST'][0][1]
    assert state==dict(speed=w(0x2a),target=w(0x2c),rpm=w(0x22)),('recurrent_input',tick,state)
    assert carry==ac[3],('acceleration_carry',tick,carry,ac[3])
    speed=state['speed'];rpm=state['rpm'];drag=read(read(param+0x304,'I')+2*(speed>>10),'h')
    acceleration=word(sw(0x1e)-drag);torque=None
    assert analog==0 and input_byte&3==1,(tick,input_byte,analog)
    if rpm>pw(0xc):rpm=pw(0xc)-1;acceleration=word(acceleration-pw(4));branch='rev_limit'
    elif car[0xca]:rpm=(rpm-16)&65535;branch='clutch'
    elif not car[0xc0]:
        if rpm<pw(0xc) and speed<64000:acceleration=word(acceleration+768)
        branch='airborne_throttle'
    else:
        torque=pb(0x3a) if car[0xbe]<=1 and sw(0x22)<2600 else pb(0x3b+(rpm>>7))
        if car[0xc6] and sw(0x22)<5000:torque=(torque+pb(0x3a))//2
        addition=((torque*w(0x32))&65535)>>4
        acceleration=word(acceleration+addition)
        acceleration=word(trunc(acceleration*25,pw(2))>>1)
        branch='grounded_torque'
    assert acceleration==ac[2],(tick,branch,acceleration,ac[2],drag,torque)
    assert rpm==ac[5],('rpm_before',tick,rpm,ac[5])
    numerator=2*acceleration+carry;scaled=trunc(numerator,5);carry=numerator-scaled*5
    new_speed=(speed+scaled)&65535 if scaled>=0 else max(0,speed+scaled)
    if scaled>=0 and speed>=32768 and (new_speed<32768 or new_speed>62720):new_speed=62720
    target=state['target']
    if car[0xc0]:
        if abs(word(target-new_speed))>5120:new_speed=(speed+target)//2
        target=new_speed
    assert (new_speed,target)==(sy[3],sy[4]),('recurrent_sync',tick,new_speed,target,sy[3:5])
    rpm_after=max(pw(6),rpm if car[0xca] else (new_speed*w(0x30))>>16)
    state=dict(speed=new_speed,target=target,rpm=rpm_after)
    distance,distance_carry=divmod(2*((target*1408)//15360)+distance_carry,5)
    assert [distance,distance_carry]==r['DIST_END'][tick-451][1:],('recurrent_distance',tick)
    assert rpm_after==en[2],('rpm_after',tick,rpm_after,en[2])
    branches[branch]+=1;rows.append(dict(tick=tick,branch=branch,slope=sw(0x1e),drag=drag,torque=torque,nominal_acceleration=acceleration,rpm_before=rpm,rpm_after=rpm_after,param_pointer=param,speed=new_speed,target=target,distance=distance,acceleration_carry=carry,distance_carry=distance_carry))
report=dict(steps=len(rows),branches=dict(branches),parameter_pointers=sorted(set(v['param_pointer'] for v in rows)),matching_full_states=data['matching_full_states'],rows=rows,scope='350-step recurrent speed/target/RPM and both acceleration/distance carries, seeded only once. Nominal acceleration recalculated from immutable original tables. Gear/clutch/cooldown and contact/slope inputs remain observed; not a full vehicle recurrence.')
(cap/'scalar-recurrence-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('rows','scope')},indent=2))
