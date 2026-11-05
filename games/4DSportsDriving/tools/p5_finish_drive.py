#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
from profile_window import command
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());a=m['data_base']+0x7ffe;s=m['clock_symbols'];rows=[];steer=0x4e;gas=0x4c;control=False

def key(k,pressed):command(f'gdb monitor key {k:x} {pressed}')
def sample():
 q={'x':(a-0x92e,'int'),'z':(a-0x926,'int'),'outcome':(a-0x865,'char'),'crossed':(a-0x861,'char'),'speed':(a-0x902,'short'),'heading':(a-0x916,'short'),'consumer':(a-0x940,'short'),'mode':(a+0x45,'char'),**{k:(v,'int' if k in ('sim_clock_fields','sim_schedule_ticks','perf_failure') else 'short') for k,v in s.items()}}
 t=command('gdb '+'\n'.join(f'p /u *(unsigned {f} *){p:#x}' for p,f in q.values()));v=list(map(int,re.findall(r'^\$\d+ = (\d+)',t,re.M)));assert len(v)==len(q),t;r=dict(zip(q,v));r['queue']=(r['sim_schedule_write']-r['sim_schedule_read'])&65535;rows.append(r);assert r['sim_schedule_overflow']==r['perf_failure']==0;return r
key(0x4e,1);r=sample();start=r['sim_clock_fields'];turn_phase=0
rate=json.loads((cap/'window.json').read_text())['start']['rate'];pulse=rate in (20,50)
while not r['outcome'] and r['sim_clock_fields']-start<2500:
 control=control or bool(r['crossed'])
 low,high=(0x0f00,0x1400) if control and pulse else (0x2000,0x2800)
 want=0x4d if r['speed']>high else 0x4c if r['speed']<low else gas
 if want!=gas:key(gas,0);key(want,1);gas=want
 if not control and pulse:
  want=0x4e if turn_phase%10<(6 if rate==50 else 5) else 0
  if want!=steer:
   if steer:key(steer,0)
   if want:key(want,1)
   steer=want
  turn_phase+=1
 if control:
  heading=r['heading']&1023;heading=heading-1024 if heading>=512 else heading
  import math
  target=round(-math.atan2(493824-r['x'],12000)*1024/(2*math.pi)) if pulse else 0
  error=(heading-target+512)%1024-512
  want=0x4e if error>8 else 0x4f if error< -8 else 0
  if want!=steer:
   if steer:key(steer,0)
   if want:key(want,1)
   steer=want
 command('gdb monitor fields 5');r=sample()
key(gas,0)
if steer:key(steer,0)
command('shot '+str(cap/'finish.png'))
report={'rows':rows,'outcome':r['outcome'],'queue_max_at_samples':max(x['queue'] for x in rows),'overflow':0,'slave_sha256':m['slave_sha256'],'scope':'Matching 50 Hz build, disposable scenery-cleared/water fixture, keyboard-only controller with 60% steering pulses before crossing and feedback afterward; no guest-state writes.'}
(cap/'finish-check.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='rows'},flush=True);assert r['outcome']==3
