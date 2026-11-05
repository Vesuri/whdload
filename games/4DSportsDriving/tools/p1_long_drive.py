#!/usr/bin/env python3
import json,struct,re,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());a=m['data_base']+0x7ffe;s=m['clock_symbols'];rows=[]
def sample():
 q={**{k:(v,'I' if k in ('sim_clock_fields','sim_schedule_ticks','perf_failure') else 'H') for k,v in s.items()},'consumer':(a-0x940,'H'),'mode':(a+0x45,'B'),'outcome':(a-0x865,'B'),'speed':(a-0x902,'H')}
 out=command('gdb '+'\n'.join(f'p /u *(unsigned '+{'I':'int','H':'short','B':'char'}[f]+f' *){p:#x}' for p,f in q.values()));v=list(map(int,re.findall(r'^\$\d+ = (\d+)',out,re.M)));assert len(v)==len(q),out
 r=dict(zip(q,v));r['queue']=(r['sim_schedule_write']-r['sim_schedule_read'])&65535;rows.append(r);assert r['sim_schedule_overflow']==r['perf_failure']==0;return r
start=sample();target=start['sim_clock_fields']+120*start['sim_time_field_hz']
while rows[-1]['sim_clock_fields']<target:
 command(f'gdb monitor fields {min(250,target-rows[-1]["sim_clock_fields"])}');sample()
command('shot '+str(cap/'long-drive.png'))
r={'slave_sha256':m['slave_sha256'],'rows':rows,'observed_seconds':(rows[-1]['sim_clock_fields']-start['sim_clock_fields'])/start['sim_time_field_hz'],'queue_max_at_samples':max(x['queue'] for x in rows),'overflow':0,'outcomes':sorted(set(x['outcome'] for x in rows)),'scope':'Held-throttle stock-track 120-second field-clock observation; outcome and moving-step counts recorded explicitly. Does not by itself prove a finish or continuous movement after an outcome.'}
(cap/'long-drive.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k!='rows'},flush=True)
