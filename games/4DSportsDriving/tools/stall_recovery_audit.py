#!/usr/bin/env python3
"""Audit continuous publication and consumed input through a main-task stall."""
import json,re,struct,sys
from pathlib import Path
cap=Path(sys.argv[1]);expected=int(sys.argv[2])
m=json.loads((cap/'anchor.json').read_text());r=json.loads((cap/'capacity-window.json').read_text())
b=(cap/'capacity-end.bin').read_bytes()
sy={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['marker']+8-sy['tape_game']-m['memory_base'];aa=m['data_base']+0x7ffe-m['memory_base']
read=lambda n,fmt='I':struct.unpack_from('>'+fmt,b,base+sy[n])[0]
start,end=read('sim_stall_start'),read('sim_stall_end')
assert read('sim_stall_done','H')==1 and end-start==expected
assert read('sim_schedule_overflow','H')==read('perf_failure')==0
write=read('sim_schedule_write','H')
queued=[]
for i in range(256):
 field,control,steering,analogue,pad=struct.unpack_from('>IBbBB',b,base+sy['sim_schedule_queue']+8*((write-256+i)&255))
 queued.append(dict(field=field,control=control,steering=steering,analogue=analogue,pad=pad))
byfield={v['field']:v for v in queued}
window=[byfield[i] for i in range(r['start']['fields']+1,r['end']['fields']+1)]
assert len(window)==250 and all(v['control']==1 and v['analogue']==0 for v in window)
history=struct.unpack_from('>I',b,aa-0x1770)[0]-m['memory_base']
complete=r['completion_samples']
for v in complete:
 assert b[history+v['tick']-1]==byfield[v['input_field']]['control']
assert all(y['tick']==x['tick']+1 and y['input_field']==x['input_field']+1 for x,y in zip(complete,complete[1:]))
inside=[v for v in r['field_samples'] if start<v['fields']<end]
if expected:
 assert len(inside)==expected-1
 assert len(set(v['completed'] for v in inside))==1
recovered=next((v for v in r['field_samples'] if v['fields']>=end and v['complete_step_debt']<=2),None)
assert recovered is not None
report=dict(stall_fields=expected,stall_start=start,stall_end=end,
 published_fields=250,completed_steps=len(complete),verified_native_history_inputs=len(complete),
 max_complete_step_debt=r['max_complete_step_debt'],
 first_debt_at_most_two_field=recovered['fields'],
 recovery_fields_after_stall=recovered['fields']-end,
 input_age=r['input_to_completion_fields'],crash_flags=[b[aa-0x92e+0xc9],b[aa-0x85e+0xc9]],
 scope='Private one-shot main-task stall at scheduler poll; field clock and native input.device throttle remain active. Retained timestamped queue bytes agree with consumed native history. No state equivalence claim until paired comparison.')
(cap/'stall-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
