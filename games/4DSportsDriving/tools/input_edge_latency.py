#!/usr/bin/env python3
"""Join real input.device requests to sampled controls and proved display chains."""
import argparse,json,re,struct
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--steering',action='store_true');a=p.parse_args();cap=a.capture
m=json.loads((cap/'anchor.json').read_text());listing=(cap/'slave.lst').read_text(encoding='latin1');s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',listing,re.M)};base=m['marker']+8-s['tape_game']
lines=[x for x in listing.splitlines() if x.startswith('00:') and x.rstrip().endswith('move.l sim_clock_fields(pc),(a0)+') and s['sim_schedule_field']<=int(x[3:11],16)<s['sim_schedule_poll']];assert len(lines)==1;publish=base+int(lines[0][3:11],16)
end=(cap/'end-memory.bin').read_bytes();o=base+s['tape_edge_phase']-m['memory_base'];assert struct.unpack_from('>H',end,o)[0]==4
aa=m['data_base']+0x7ffe-m['memory_base'];rel=base-m['memory_base']
u16=lambda o:struct.unpack_from('>H',end,o)[0];u32=lambda o:struct.unpack_from('>I',end,o)[0]
checks=dict(rate=u16(aa-0x15fa),mode=end[aa+0x45],active=u16(rel+s['sim_schedule_active']),modal=u16(rel+s['sim_schedule_modal']),overflow=u16(rel+s['sim_schedule_overflow']),failure=u32(rel+s['perf_failure']))
assert checks==dict(rate=50,mode=0,active=1,modal=0,overflow=0,failure=0),checks
records=[dict(zip(('request_clock','return_clock','raw_key','io_error','consumer','index'),struct.unpack_from('>II4H',end,o+4+i*16))) for i in range(4)]
keys=[0x4f,0xcf,0x4e,0xce] if a.steering else [0xcc,0x4c,0xcc,0x4c]
expected=[9,1,5,1] if a.steering else [0,1,0,1]
assert ('tape_edge_steering_keys' in s)==a.steering
assert [r['raw_key'] for r in records]==keys
assert all(r['io_error']==0 and r['request_clock']<=r['return_clock'] for r in records)
assert all(b['request_clock']-a['return_clock']==40 for a,b in zip(records,records[1:]))
latency=json.loads((cap/'presentation-latency.json').read_text());containing={r['sample']:r for r in latency['steps_contained_in_displayed_states']}
t=barto.load(cap/'trace.bin');boundaries=barto.capture_part_starts(cap,t);events={};pending=None;prev=None;seq=0
for f in t.fields:
 if f.index in boundaries:pending=None;prev=None
 for pc,c,r in t.instructions(f):
  seq+=1
  if pc==base+s['tape_edge_send']:
   index=r[7]&65535;assert index not in events and 0<=index<4
   assert r[3]&65535==records[index]['raw_key']
   pending=dict(index=index,request_field=f.index,request_order=seq,raw_key=r[3]&65535,expected=expected[index])
   events[index]=pending
  elif pc==base+s['tape_edge_return']:
   index=r[7]&65535
   if index in events:events[index]['return_field']=f.index
  elif pc==publish:
   value=r[5]&255
   if pending is not None and 'sample_field' not in pending and value==pending['expected']:
    assert prev is not None and prev!=value,'no observed input edge'
    pending.update(sample_field=f.index,sample_order=seq,previous=prev,sampled=value)
   prev=value
out=[]
for i in range(4):
 row=dict(records[i],trace=events.get(i))
 e=events.get(i)
 if e is not None and 'sample_field' in e:
  e['request_to_sample_fields']=e['sample_field']-e['request_field']
  step=containing.get(e['sample_field'])
  if step:
   e.update(completed_field=step['completed'],visible_field=step['visible'],request_to_completed_fields=step['completed']-e['request_field'],request_to_containing_display_fields=step['visible']-e['request_field'])
  else:e['display_excluded']='No complete chain inside one capture part'
 out.append(row)
assert len(events)==4 and all('sample_field' in x for x in events.values()),out
assert all('visible_field' in e for e in events.values()),out
r=dict(controls="steering" if a.steering else "throttle",fields=250,end_checks=checks,edges=out,scope='Ordinary Amiga input.device requests, not host keyboard arrival. First sampled changed control must follow the request in instruction order. Display means first proved displayed state containing that physics step, not a claim of visible pixel response. Capture joins excluded.')
(cap/'input-edge-latency.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
