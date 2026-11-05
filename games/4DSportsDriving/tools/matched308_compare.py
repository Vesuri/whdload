#!/usr/bin/env python3
"""Check aligned15.4s matched-car landing and natural native reproduction."""
import argparse,hashlib,json
from pathlib import Path
from simulation_fixture import read_fixture
P=Path(__file__).resolve().parents[1]/'tmp'
seed=(P/'fixtures/matched-landing308/car.bin').read_bytes()
parser=argparse.ArgumentParser();parser.add_argument('--candidate',default='matched308-50');parser.add_argument('--output',default='matched308-comparison.json');args=parser.parse_args()
assert '/' not in args.candidate and '/' not in args.output
paths={20:P/'prof/matched308-20',50:P/'prof'/args.candidate}
data={};provenance={}
for hz,p in paths.items():
    samples=read_fixture(p)
    assert samples[0][:2]==(0,hz)
    assert samples[0][2][0x152:0x222]==seed
    assert not any(samples[0][2][0x466:0x466+152])
    d=json.loads((p/'landing-motion-check.json').read_text())
    assert d['rate']==hz
    data[hz]={r['tick']:r for r in d['rows']}
    provenance[str(hz)]=dict(slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),motion_sha256=hashlib.sha256((p/'landing-motion-check.json').read_bytes()).hexdigest(),seed_sha256=hashlib.sha256(seed).hexdigest(),private_zero=True)
reference=json.loads((P/'prof/crest-landing20/landing-motion-check.json').read_text())
ref={r['tick']:r for r in reference['rows']}
for tick,r in data[20].items():
    native=ref[tick+308]
    assert all(r[k]==native[k] for k in native if k!='tick'),tick
rows=[]
for n in range(1,7):
    a=data[20][2*n];b=data[50][5*n]
    ap=data[20][2*n+1];bp=data[50][5*n+1]
    signed=lambda x:(x+32768)%65536-32768
    rows.append(dict(elapsed=n/10,original_time=15.4+n/10,native_pitch=signed(ap['angles'][1]),candidate_pitch=signed(bp['angles'][1]),pitch_error=signed(bp['angles'][1])-signed(ap['angles'][1]),native_position=a['final_position'],candidate_position=b['final_position'],position_error=[v-u for u,v in zip(a['final_position'],b['final_position'])],native_extensions=ap['extension'],candidate_extensions=bp['extension']))
report=dict(provenance=provenance,native_exact_updates=len(data[20]),rows=rows,critical=rows[1],scope='Exact native car seed from15.4s; both modes have zero private fractions. Native motion fields reproduce natural run. Measurements align at100ms boundaries, including original15.6s. This diagnoses local response without replacing full-course acceptance criteria.')
(P/'prof'/args.output).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
