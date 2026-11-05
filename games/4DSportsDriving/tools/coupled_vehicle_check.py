#!/usr/bin/env python3
"""Closed feedback recurrence of straight stock-car drivetrain/contact/body.

Seeded from anchor RAM; held throttle and immutable terrain/car tables.
Collision side effects, rendering, replay and arbitrary steering are not modeled.
"""
import json,struct,sys,hashlib
from pathlib import Path
from drivetrain_model import step as engine
from contact_step import step as contact
from native_contact_response import rotate
from simulation_fixture import read_fixture
root=Path('tmp/prof');phase=sys.argv[2] if len(sys.argv)>2 else 'nominal';assert phase in ('nominal','minus64','plus64')
cap=root/('drivetrain-feedback-inputs-d9' if phase=='nominal' else 'contact-prediction-d9-'+phase+'-long');m=json.loads((cap/'anchor.json').read_text());ram=(cap/'memory.bin').read_bytes();base=m['memory_base'];co=m['data_base']+0x7ffe-0x92e-base;private=ram.index(b'4DA4PHYS')+12
read=lambda a,f:struct.unpack_from('>'+f,ram,a-base)[0]
car=bytearray(ram[co:co+208]);carry=dict(zip(('acceleration','distance','gear'),struct.unpack_from('>hHh',ram,private+2)))
ref=json.loads((root/'drivetrain-feedback-inputs-d9/drivetrain.json').read_text())['records'];param=ref['PRE_ENGINE'][0][1]
assert m['data_base']==5689288,'Stock car parameter relocation needs explicit resolution'
baseline='crest-d9e7903' if phase=='nominal' else 'phase-'+phase+'-d9'
bridge={r['tick']:r for r in json.loads((root/baseline/'bridge.json').read_text())['rows']}
trace=json.loads((root/('contact-prediction-d9-long' if phase=='nominal' else 'contact-prediction-d9-'+phase+'-long')/'prediction.json').read_text())['records'];entries={r[0]:r for r in trace['ENTRY']};bodies={r[0]:r[1:] for r in trace['BODY']}
def unpack(fmt,data,off):return list(struct.unpack_from('>'+fmt,data,off))
e=[451]+unpack('3h',car,0x18)+[0]*9+unpack('4h',car,0x54)+unpack('4h',car,0x6c)+unpack('4h',car,0x4c)
e += [read(base+private+off+4*w,'h') for off in (8,10) for w in range(4)]
e += unpack('4h',ram,private+24)+unpack('4h',ram,private+40)+unpack('h',ram,private+144)+unpack('3H',ram,private+132)+[0]*24
assert len(e)==69
state=dict(entry=e,position=unpack('3i',car,0),cached=[unpack('3h',car,0x74+6*w) for w in range(4)])
mode=sys.argv[1] if len(sys.argv)>1 else 'baseline';solver=None
if mode=='chronological':from chronological_contact_model import solve as solver
elif mode=='support-release':from support_release_force_model import solve as solver
elif mode=='query-crossing':from query_crossing_budget_model import solve as solver
else:assert mode=='baseline'
rows=[];checks=0;sample_checks=0
samples={t:s for t,hz,s in read_fixture(root/baseline,'bridge-end.bin')}
fields=[(o,'H') for o in (0x22,0x24,0x28,0x2a,0x2c,0x2e,0x30,0x32,0x34,0x38,0x3a,0x3c)]+[(o,'B') for o in (0xbe,0xc6,0xca,0xcb,0xcc)]
for t in range(451,801):
    car[0xc0]=sum(bool(v) for v in car[0xc4:0xc6]);car[0xc1]=sum(bool(v) for v in car[0xc2:0xc6])
    car,carry,eng=engine(car,carry,param,read)
    state,rec=contact(state,50,eng['distance'],body_solver=solver);out=rec['output']
    struct.pack_into('>h',car,0x1e,-rotate([0,0,130],rec['entry'][4:13])[1])
    for w,result in enumerate(out['wheels']):car[0xc2+w]=int(result['suspension_clearance']<=12)
    wcar=lambda o:struct.unpack_from('>H',car,o)[0]
    if mode=='baseline':
        assert rec['entry']==entries[t],('contact entry',t)
        assert out['position']+[0,out['pitch'],0,out['pitch_carry']]+out['centroid_carries']==bodies[t],('body',t)
        assert eng['distance']==next(v['distance'] for v in trace['SELECT'] if v['tick']==t and v['wheel']==0),('distance',t)
        assert wcar(0x2a)==bridge[t]['speed'],('engine_speed',t)
        if phase=='nominal':
            actual=struct.pack('>104H',*ref['PRE_ENGINE'][t-451][4:])
            for offset,fmt in fields:
                assert struct.unpack_from('>'+fmt,eng['pre_engine'],offset)==struct.unpack_from('>'+fmt,actual,offset),('engine',t,hex(offset))
        if t in samples:
            for offset,fmt in fields:
                actual=struct.unpack_from('>'+fmt,samples[t],0x152+offset)[0]
                predicted=struct.unpack_from('>'+fmt,car,offset)[0]
                assert actual==predicted,('complete_sample_engine',t,hex(offset),actual,predicted)
            sample_checks+=1
        checks+=1
    rows.append(dict(tick=t,x=out['position'][0],y=out['position'][1],z=out['position'][2],pitch=out['pitch'],distance=eng['distance'],speed=wcar(0x2a),target=wcar(0x2c),rpm=wcar(0x22),gear=car[0xbe],clutch=car[0xca],flags=list(car[0xc2:0xc6]),carry=carry.copy()))
report=dict(mode=mode,phase=phase,exact_baseline_steps=checks,complete_sample_engine_checks=sample_checks,rows=rows,model_sha256=hashlib.sha256(Path('tools/drivetrain_model.py').read_bytes()).hexdigest(),scope=__doc__)
(root/('coupled-vehicle-'+mode+('' if phase=='nominal' else '-'+phase)+'.json')).write_text(json.dumps(report,indent=2,default=str)+'\n');print(mode,'exact baseline steps',checks,'final',rows[-1])
