#!/usr/bin/env python3
"""Equal-car-state local landing comparison; not a replacement acceptance gate."""
import hashlib,json,struct
from pathlib import Path
from simulation_fixture import read_fixture
P=Path(__file__).resolve().parents[1]/'tmp'
seed=(P/'fixtures/matched-landing/car.bin').read_bytes()
paths={20:P/'prof/matched-landing20',50:P/'prof/matched-landing50-tick3'}
data={};reports={}
for hz,p in paths.items():
    samples=read_fixture(p)
    assert samples[0][0]==0 and samples[0][1]==hz
    assert samples[0][2][0x152:0x222]==seed
    assert not any(samples[0][2][0x466:0x466+152])
    d=json.loads((p/'landing-motion-check.json').read_text())
    assert d['rate']==hz
    data[hz]={r['tick']:r for r in d['rows']}
    reports[str(hz)]=dict(capture=str(p),slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),initial_car_sha256=hashlib.sha256(samples[0][2][0x152:0x222]).hexdigest(),private_fractions_zero=True,updates=d['updates'])
rows=[]
for tenth in range(1,6):
    a=data[20][tenth*2];anext=data[20][tenth*2+1]
    b=data[50][tenth*5];bnext=data[50][tenth*5+1]
    signed=lambda n:(n+32768)%65536-32768
    na=signed(anext['angles'][1]);ca=signed(bnext['angles'][1])
    rows.append(dict(seconds=tenth/10,native_position=a['final_position'],candidate_position=b['final_position'],position_error=[y-x for x,y in zip(a['final_position'],b['final_position'])],native_pitch=na,candidate_pitch=ca,pitch_error=ca-na,native_extensions=anext['extension'],candidate_extensions=bnext['extension']))
report=dict(captures=reports,common_time=rows,max_common_100ms_pitch_error=max(abs(r['pitch_error']) for r in rows),scope='Identical native car state at synthetic tick0, zero private fractions, equal throttle. Native fixture exactly reproduces10 original natural-landing updates across all recorded motion fields. Common-time pitch is taken from the NEXT update entry, paired with current completed position. Diagnostic only: no new tolerance or full-course acceptance claim.')
native_mid=(data[20][4]['angles'][1]+32768)%65536-32768
brackets=[dict(seconds=(tick-1)/50,pitch=(data[50][tick]['angles'][1]+32768)%65536-32768) for tick in (8,9)]
report['native_150ms_bracket']=dict(native_pitch=native_mid,candidate_brackets=brackets,scope='No50Hz endpoint at150ms for this seed phase. Do not use the100ms common-sample maximum as a bound on transient error.')
(P/'prof/matched-landing-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
