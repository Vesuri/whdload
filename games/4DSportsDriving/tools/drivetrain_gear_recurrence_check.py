#!/usr/bin/env python3
"""Validate automatic gearing/cooldowns plus scalar drivetrain from one seed."""
import json,struct,collections
from pathlib import Path
from drivetrain_model import step
cap=Path('tmp/prof/drivetrain-feedback-inputs-d9');r=json.loads((cap/'drivetrain.json').read_text())['records'];m=json.loads((cap/'anchor.json').read_text());ram=(cap/'memory.bin').read_bytes();base=m['memory_base'];co=m['data_base']+0x7ffe-0x92e-base;private=ram.index(b'4DA4PHYS')+12
read=lambda a,f:struct.unpack_from('>'+f,ram,a-base)[0]
car=bytearray(ram[co:co+208]);carry=dict(zip(('acceleration','distance','gear'),struct.unpack_from('>hHh',ram,private+2)))
fields=[(o,'H') for o in (0x22,0x24,0x28,0x2a,0x2c,0x2e,0x30,0x32,0x34,0x38,0x3a,0x3c)]+[(o,'B') for o in (0xbe,0xc6,0xca,0xcb,0xcc)]
rows=[];branches=collections.Counter()
for pre,ac,en,di in zip(*(r[k] for k in ('PRE_ENGINE','ACCEL','ENGINE_END','DIST_END'))):
    t,param,inp,analog,*words=pre;actual=struct.pack('>104H',*words)
    # Contact and slope only are externally supplied in this intermediate check.
    car[0x1e:0x20]=actual[0x1e:0x20];car[0xc0:0xc2]=actual[0xc0:0xc2]
    car,carry,out=step(car,carry,param,read,inp,analog)
    for offset,fmt in fields:
        a=struct.unpack_from('>'+fmt,out['pre_engine'],offset)[0];b=struct.unpack_from('>'+fmt,actual,offset)[0]
        assert a==b,('pre_engine',t,hex(offset),a,b)
    assert out['nominal_acceleration']==ac[2],('acceleration',t)
    w=lambda o:struct.unpack_from('>H',car,o)[0]
    assert [w(0x22),w(0x2a),w(0x2c)]==[en[2],en[3],en[4]],('engine_end',t)
    assert [out['distance'],carry['distance']]==di[1:],('distance',t)
    branches[out['branch']]+=1;rows.append(dict(tick=t,gear=car[0xbe],clutch=car[0xca],cooldown=car[0xc6],carry=carry.copy(),speed=w(0x2a),target=w(0x2c),rpm=w(0x22),distance=out['distance']))
report=dict(steps=len(rows),pre_engine_fields_per_step=len(fields),branches=dict(branches),rows=rows,scope='Gear, clutch, timers, speed, target, RPM and carries recurrently predicted from anchor. Only contact-count and slope inputs externally supplied. Held throttle, stock car, straight course; not arbitrary vehicle validation.')
(cap/'gear-recurrence-check.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('rows','scope')})
