#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
from simulation_fixture import read_fixture
P=Path(__file__).resolve().parents[1]/'tmp'
parser=argparse.ArgumentParser();parser.add_argument('--candidate',default='matched-takeoff50');parser.add_argument('--output',default='matched-takeoff-comparison.json');args=parser.parse_args()
assert '/' not in args.candidate and '/' not in args.output
seed=(P/'fixtures/matched-takeoff222/car.bin').read_bytes();data={};proof={}
for hz in (20,50):
 p=P/'prof'/('matched-takeoff20' if hz==20 else args.candidate);samples=read_fixture(p)
 assert samples[0][:2]==(0,hz) and samples[0][2][0x152:0x222]==seed
 assert not any(samples[0][2][0x466:0x466+152])
 d=json.loads((p/'landing-motion-check.json').read_text());data[hz]={r['tick']:r for r in d['rows']}
 proof[str(hz)]=dict(slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),seed_sha256=hashlib.sha256(seed).hexdigest(),observed_updates=d['updates'])
ref={r['tick']:r for r in json.loads((P/'prof/natural-crest20/bridge.json').read_text())['rows']}
for tick,r in data[20].items():
 original=ref[tick+222];assert r['final_position']==[original[k] for k in ('x','y','z')]
 if tick+1 in data[20]:assert data[20][tick+1]['angles']==[original[k]%65536 for k in ('heading','pitch','roll')]
rows=[]
for n in range(1,7):
 a=data[20][2*n];b=data[50][5*n];ap=data[20][2*n+1];bp=data[50][5*n+1];signed=lambda v:(v+32768)%65536-32768
 # At common100ms endpoints all constant gravity increments have integer
 # fifths only if release phase aligns; these are observed integer car words.
 rows.append(dict(elapsed=n/10,native_pitch=signed(ap['angles'][1]),candidate_pitch=signed(bp['angles'][1]),pitch_error=signed(bp['angles'][1])-signed(ap['angles'][1]),position_error=[v-u for u,v in zip(a['final_position'],b['final_position'])],native_velocity_words=ap['wheel_velocity'],candidate_velocity_words=bp['wheel_velocity'],native_extensions=ap['extension'],candidate_extensions=bp['extension']))
report=dict(proof=proof,native_exact_positions=len(data[20]),rows=rows,scope='Identical native car seed at11.1s, private fractions zero. Native captured positions/angles exactly reproduce natural course. A4000 uses actual-and-reference local stabilization guard. Velocity words omit private fifth fractions; do not treat fractional values as observed. Diagnostic only, no new handling tolerance.')
(P/'prof'/args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
