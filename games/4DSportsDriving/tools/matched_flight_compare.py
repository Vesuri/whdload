#!/usr/bin/env python3
"""Validate equal initial airborne state, exact gravity and native reproduction."""
import hashlib,json
from pathlib import Path
from simulation_fixture import read_fixture
P=Path(__file__).resolve().parents[1]/'tmp'
seed=(P/'fixtures/matched-flight232/car.bin').read_bytes()
data={};proof={}
for hz in (20,50):
 p=P/f'prof/matched-flight{hz}';samples=read_fixture(p)
 assert samples[0][:2]==(0,hz) and samples[0][2][0x152:0x222]==seed
 assert not any(samples[0][2][0x466:0x466+152])
 d=json.loads((p/'landing-motion-check.json').read_text());data[hz]={r['tick']:r for r in d['rows']}
 count=0
 for r in d['rows']:
  k=r['tick'];assert r['extension']==[384]*4
  for w in range(4):
   v,a=(189,21) if w<2 else (105,15)
   expected=v+(a*(k-1)*20)//hz
   assert r['wheel_velocity'][w]==expected,(hz,k,w,r['wheel_velocity'],expected)
   total=lambda n:v*n+a*n*(n+1)//2 if hz==20 else (10*v*n+a*(2*n*n+5*n))//25
   before=r['wheel_stages']['translated'][w];after=r['wheel_stages']['contact'][w]
   assert [after[i]-before[i] for i in range(3)]==[0,-(total(k)-total(k-1)),0],(hz,k,w,before,after)
   count+=1
 proof[str(hz)]=dict(slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),seed_sha256=hashlib.sha256(seed).hexdigest(),exact_gravity_steps=count,all_extensions_384=True)
ref={r['tick']:r for r in json.loads((P/'prof/natural-crest20/bridge.json').read_text())['rows']}
for tick,r in data[20].items():
 original=ref[tick+232]
 assert r['final_position']==[original[k] for k in ('x','y','z')]
 if tick+1 in data[20]:
  assert data[20][tick+1]['angles']==[original[k]%65536 for k in ('heading','pitch','roll')]
rows=[]
for n in range(1,7):
 a=data[20][2*n];b=data[50][5*n];ap=data[20][2*n+1];bp=data[50][5*n+1];signed=lambda v:(v+32768)%65536-32768
 rows.append(dict(elapsed=n/10,native_pitch=signed(ap['angles'][1]),candidate_pitch=signed(bp['angles'][1]),pitch_error=signed(bp['angles'][1])-signed(ap['angles'][1]),position_error=[v-u for u,v in zip(a['final_position'],b['final_position'])],native_velocity=ap['wheel_velocity'],candidate_velocity=bp['wheel_velocity']))
report=dict(proof=proof,native_exact_positions=len(data[20]),rows=rows,scope='Identical car seed from native11.6s. All observed wheel gravity displacements and pre-update velocities match independently evaluated ordered-pair arithmetic. Extensions remain384; gravity stage has no X/Z change or contact correction. Native positions and subsequent angles reproduce the original course. Diagnostic only; no full-course acceptance claim.')
(P/'prof/matched-flight-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
