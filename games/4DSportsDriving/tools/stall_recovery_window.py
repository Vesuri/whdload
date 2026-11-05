#!/usr/bin/env python3
"""Measure a continuous 250-field window between identical post-producer IRQ sites."""
import argparse,json,re,struct
from pathlib import Path
from profile_window import command,ROOT
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--name',default='capacity');p.add_argument('--sample-fields',action='store_true');a=p.parse_args();cap=a.capture.resolve()
m=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes()
s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
base=m['marker']+8-s['tape_game'];irq=base+s['sim_clock_interrupt']+10
assert b[irq-m['memory_base']:irq-m['memory_base']+8]==bytes.fromhex('4cdf7ffe70004e75')
clock=base+s['sim_clock_fields']
def stop(condition=''):
 r=command(f'gdb delete\ntbreak *{irq:#x}'+(' if '+condition if condition else '')+'\ncontinue\ninfo registers pc');print(r,flush=True)
 assert int(re.search(r'^pc\s+0x([0-9a-f]+)',r,re.M)[1],16)==irq

def snapshot(name):
 f=cap/name;command(f'gdb dump binary memory {f.relative_to(ROOT)} 0x200000 0x600000');b=f.read_bytes()
 u16=lambda off:struct.unpack_from('>H',b,off)[0];u32=lambda off:struct.unpack_from('>I',b,off)[0]
 sy=lambda n:base+s[n]-m['memory_base'];aa=m['data_base']+0x7ffe-m['memory_base']
 r=dict(fields=u32(sy('sim_clock_fields')),produced=u32(sy('sim_schedule_ticks')),consumed=u16(aa-0x940),imported=u16(aa+0xa0),queue=(u16(sy('sim_schedule_write'))-u16(sy('sim_schedule_read')))&65535,overflow=u16(sy('sim_schedule_overflow')),frames=u32(sy('tape_frames')),active=u16(sy('sim_schedule_active')),modal=u16(sy('sim_schedule_modal')),mode=b[aa+0x45],rate=u16(aa-0x15fa),opponent=b[aa-0x174a],failure=u32(sy('perf_failure')))
 r['debt']=r['queue']+((r['imported']-r['consumed'])&65535)
 return r
stop();start=snapshot(a.name+'-start.bin');assert start['active']==1 and start['rate']==50 and start['mode']==0 and not start['modal']
rows=[];completions=[]
if a.sample_fields:
 aa=m['data_base']+0x7ffe
 specs=[('fields',clock,32),('produced',base+s['sim_schedule_ticks'],32),('consumed',aa-0x940,16),('imported',aa+0xa0,16),('read',base+s['sim_schedule_read'],16),('write',base+s['sim_schedule_write'],16),('frames',base+s['tape_frames'],32),('input_field',base+s['sim_schedule_current'],32)]
 args=', '.join(f'*(unsigned {"int" if width==32 else "short"} *){addr:#x}' for _,addr,width in specs)
 fmt='FIELD '+' '.join(['%u']*len(specs))+r'\n'
 # Count only the fully completed native coordinator body, at E7B4.
 specs.append(('completed',None,None));fmt='FIELD '+' '.join(['%u']*len(specs))+r'\n';args+=', $completed'
 script=f'gdb delete\nset $completed=0\nbreak *{m["game_base"]+0xe7b4:#x}\ncommands\nsilent\nset $completed=$completed+1\nprintf "COMPLETE %u %u %u %u\\n", $completed, *(unsigned short *){aa-0x940:#x}, *(unsigned int *){clock:#x}, *(unsigned int *){base+s["sim_schedule_current"]:#x}\ncontinue\nend\nbreak *{irq:#x}\ncommands\nsilent\nprintf "{fmt}", {args}\nif *(unsigned int *){clock:#x} < {start["fields"]+250}\ncontinue\nend\nend\ncontinue\ninfo registers pc'
 dumps=''
 for tick in (150,200,250,300):
  target=(cap/f'state-{tick}.bin').relative_to(ROOT)
  dumps+=f'if *(unsigned short *){aa-0x940:#x}=={tick}\ndump binary memory {target} 0x200000 0x600000\nend\n'
 boundary=f'continue\nend\nbreak *{irq:#x}'
 assert script.count(boundary)==1
 script=script.replace(boundary,dumps+boundary)
 (cap/'stall-window.commands.gdb').write_text(script.removeprefix('gdb '))
 result=command('gdb source '+str((cap/'stall-window.commands.gdb').relative_to(ROOT)));(cap/(a.name+'-field-log.txt')).write_text(result)
 assert int(re.search(r'^pc\s+0x([0-9a-f]+)',result,re.M)[1],16)==irq
 for match in re.finditer(r'^COMPLETE (.*)$',result,re.M):
  vals=list(map(int,match[1].split()));assert len(vals)==4
  completion=dict(zip(('ordinal','tick','field','input_field'),vals))
  completion['input_to_completion_fields']=completion['field']-completion['input_field']
  completions.append(completion)
 assert [x['ordinal'] for x in completions]==list(range(1,len(completions)+1))
 assert all(y['tick']==x['tick']+1 and y['input_field']==x['input_field']+1 for x,y in zip(completions,completions[1:])), 'missing/duplicated tick or captured field'
 for match in re.finditer(r'^FIELD (.*)$',result,re.M):
  vals=list(map(int,match[1].split()));assert len(vals)==len(specs)
  row=dict(zip([key for key,_,_ in specs],vals));row['queue']=(row['write']-row['read'])&65535
  row['debt']=row['queue']+((row['imported']-row['consumed'])&65535)
  rows.append(row)
 assert [r['fields'] for r in rows]==list(range(start['fields']+1,start['fields']+251))
else:
 stop(f'*(unsigned int *){clock:#x}=={start["fields"]+250}')
end=snapshot(a.name+'-end.bin');delta={k:end[k]-start[k] for k in ('fields','produced','consumed','frames','debt')}
r=dict(continuous=True,fields=250,seconds=5,start=start,end=end,delta=delta,all_ticks_published=delta['produced']==250,no_backlog_growth=delta['debt']<=0,all_ticks_consumed=delta['consumed']==250)
if rows:
 r['completed_steps']=rows[-1]['completed']
 r['completion_debt_change']=delta['produced']-r['completed_steps']
 r['completion_backlog_did_not_grow']=r['completion_debt_change']<=0
 r['consumer_counter_marks_entry']=True
 r['completion_samples']=completions
 if completions:
  assert len(completions)==r['completed_steps']
  start_completed=completions[0]['tick']-1
  r['start_completed_tick']=start_completed
  r['end_completed_tick']=completions[-1]['tick']
  for row in rows:
   row['complete_step_debt']=row['queue']+((row['imported']-(start_completed+row['completed']))&65535)
  r['max_complete_step_debt']=max(x['complete_step_debt'] for x in rows)
  r['min_complete_step_debt']=min(x['complete_step_debt'] for x in rows)
  latency=[x['input_to_completion_fields'] for x in completions]
  r['input_to_completion_fields']=dict(min=min(latency),max=max(latency),mean=sum(latency)/len(latency))
 r['field_samples']=rows;r['max_observed_debt']=max(x['debt'] for x in rows)
 r['min_observed_debt']=min(x['debt'] for x in rows)
 changes=[x['fields'] for prev,x in zip([start]+rows,rows) if x['frames']!=prev['frames']]
 r['max_observed_render_gap_fields']=max((y-x for x,y in zip(changes,changes[1:])),default=None)
 r['every_field_published']=all(y['produced']-x['produced']==1 for x,y in zip([start]+rows,rows))
(cap/(a.name+'-window.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ("field_samples","completion_samples")},indent=2))
assert delta['fields']==250 and delta['produced']==250 and end['overflow']==0 and end['failure']==0
