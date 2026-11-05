#!/usr/bin/env python3
"""Join captured input, completed physics and actual next-field display DMA.

Requires display_check.py on the SAME trace. Discards partial chains and never
joins separate profiler capture parts. Measures field indices, not exact ms.
"""
import argparse, collections, json, re, struct
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--render-beam-probe',action='store_true',help='Require the exact isolated render-entry JSR probe')
a=p.parse_args();cap=a.capture
m=json.loads((cap/'anchor.json').read_text())
display=json.loads((cap/'display-check.json').read_text())
listing=(cap/'slave.lst').read_text(encoding='latin1')
s={n:int(v,16) for n,v in re.findall(r'^([\w.]+)\s+00:([0-9a-fA-F]+)\s*$',listing,re.M)}
runtime=m.get('standalone_runtime',False)
base=m['slave_base'] if runtime else m['marker']+8-s['tape_game']
game=m['game_base']
mem=(cap/'memory.bin').read_bytes()
def word(addr):return struct.unpack_from('>H',mem,addr-m['memory_base'])[0]
if runtime:
 assert 'tape_game' not in s,'runtime capture contains a diagnostic build'
 aa=m['data_base']+0x7ffe
 assert word(aa-0x15fa)==50,'runtime is not using A4000 physics'
 assert word(base+s['sim_schedule_active'])==1,'runtime scheduler is inactive'
 assert word(base+s['sim_schedule_modal'])==0,'runtime is in a modal dialog'
 assert word(base+s['sim_schedule_overflow'])==0,'runtime input queue overflowed'
 assert mem[aa+0x45-m['memory_base']]==0,'runtime is not live driving'
else:
 assert m['active_simulation_word']==50
def site(source, bounds=None):
 rows=[line for line in listing.splitlines() if line.rstrip().endswith(source)]
 offsets=[int(re.match(r'00:([0-9A-Fa-f]+)',line)[1],16) for line in rows if line.startswith('00:')]
 if bounds is not None:offsets=[o for o in offsets if bounds[0]<=o<bounds[1]]
 assert len(offsets)==1,(source,offsets)
 return base+offsets[0]
publish=site('move.l sim_clock_fields(pc),(a0)+',(s['sim_schedule_field'],s['sim_schedule_poll']))
# A0 points at the selected queue payload before the two-long import.
import_site=site('lea sim_schedule_current(pc),a1')
queue=base+s['sim_schedule_queue']
# Native code hunk starts at FILE offset 0x28 (hex), not decimal 28.
off=game+0x7140-m['memory_base']
if a.render_beam_probe:
 target=base+s['sim_render_beam_probe']
 assert mem[off:off+8]==bytes.fromhex('4eb9')+struct.pack('>I',target)+bytes.fromhex('4e71'),'wrong render probe hook'
 # The diagnostic reproduces both displaced instructions before returning.
 helper=mem[target-m['memory_base']:base+s['sim_render_beam_count']-m['memory_base']]
 assert bytes.fromhex('302cf578b06cf5764e75') in helper,'missing displaced render comparison'
elif 'raster_present_prepare' in s:
 target=base+s['raster_present_prepare']
 assert mem[off:off+8]==bytes.fromhex('4eb9')+struct.pack('>I',target)+bytes.fromhex('4e71'),'wrong pipeline hook'
 helper=mem[target-m['memory_base']:base+s['raster_present_wait']-m['memory_base']]
 assert helper.endswith(bytes.fromhex('302cf578b06cf5764e75')),'missing displaced render comparison'
else:
 assert mem[off:off+4]==bytes.fromhex('302cf578'), 'wrong render-start instruction'
t=barto.load(cap/'trace.bin');boundaries=barto.capture_part_starts(cap,t)
assert sorted(boundaries)==display['capture_part_starts']
visible=dict(zip(display['displayed_transition_fields'],[None]*len(display['displayed_transition_fields'])))
visibility={(x['copper_write_field'],x['copper_list']):x['visible_field'] for x in display.get('swap_visibility',[])}
rows=[];completions=[];swaps=[];publications=[];excluded=0;event_counts=collections.Counter()
slots={};current=None;complete=None;render=None;done=set();rendering=False
wait_polls=[];wait_current=None;wait_cycles=0;total_cycles=0
wait_start=base+s['raster_present_wait'] if 'raster_present_wait' in s else -1
wait_poll=site('tst.w $d28(a4)',(s['raster_present_wait'],s['raster_present_pending'])) if wait_start>=0 else -1
wait_clear=site('clr.w (a0)',(s['raster_present_wait'],s['raster_present_pending'])) if wait_start>=0 else -1
for f in t.fields:
 if f.index in boundaries:
  slots={};current=None;complete=None;render=None;done=set();rendering=False
  wait_current=None
 for pc,c,r in t.instructions(f):
  total_cycles+=c
  if pc is not None and wait_start>=0 and wait_start<=pc<base+s['raster_present_pending']:wait_cycles+=c
  if pc==wait_start:wait_current={'start':f.index,'polls':0}
  elif pc==wait_poll and wait_current is not None:wait_current['polls']+=1
  elif pc==wait_clear and wait_current is not None:
   wait_polls.append(dict(wait_current,end=f.index));wait_current=None
  if pc in (publish,import_site,game+0xe7b4,game+0x7140,game+0x35332):event_counts[hex(pc)]+=1
  if pc==publish:
   slot=r[8]-queue
   assert 0<=slot<2048 and slot%8==0
   assert not publications or publications[-1]!=f.index,'multiple live publications in a field'
   slots[slot]=dict(sample=f.index,slot=slot);publications.append(f.index)
  elif pc==import_site:
   slot=r[8]-queue
   assert 0<=slot<2048 and slot%8==0
   current=slots.get(slot)
  elif pc==game+0xe7b4:
   assert not rendering, "physics completion inside a render"
   complete=None
   if current is not None:
    assert current['sample'] not in done,'input completed twice'
    done.add(current['sample']);complete=dict(current,completed=f.index)
    completions.append(complete)
  elif pc==game+0x7140:
   assert not rendering, "nested render"
   rendering=True
   render=dict(complete,render_start=f.index) if complete is not None else None
  elif pc==game+0x35332:
   rendering=False
   swaps.append([f.index,r[8]])
   shown=visibility.get((f.index,r[8]),f.index+1)
   if render is not None and shown in visible and shown not in boundaries:
    row=dict(render,copper_write=f.index,visible=shown,copper_list=r[8])
    assert row['sample']<=row['completed']<=row['render_start']<=row['copper_write']<=row['visible']
    rows.append(row)
   else:excluded+=1
assert swaps==display['copper_writes'],'display proof must come from identical trace'
assert rows and completions,(event_counts,hex(publish),hex(import_site),hex(queue),len(publications),len(completions),len(rows))
for lo,hi in zip(sorted(boundaries),sorted(boundaries)[1:]+[len(t.fields)]):
 pub=[x for x in publications if lo<=x<hi]
 assert len(pub)>=hi-lo-1 and all(b==a+1 for a,b in zip(pub,pub[1:])),(lo,hi,pub)
def stats(values):
 return dict(count=len(values),min=min(values),max=max(values),mean=sum(values)/len(values),histogram=dict(sorted(collections.Counter(values).items())))
containing=[]
ends=sorted(boundaries)[1:]+[len(t.fields)]
for lo,hi in zip(sorted(boundaries),ends):
 for step in completions:
  if not lo<=step['sample']<hi:continue
  candidates=[row for row in rows if lo<=row['sample']<hi and row['sample']>=step['sample'] and row['render_start']>=step['completed']]
  if candidates:
   row=candidates[0]
   containing.append(dict(step,visible=row['visible'],render_sample=row['sample']))
assert containing
result=dict(fields=len(t.fields),capture_part_starts=sorted(boundaries),input_publications=len(publications),complete_chains=len(completions),displayed_chains=len(rows),excluded_copper_writes=excluded,
 sample_to_completion_fields=stats([x['completed']-x['sample'] for x in completions]),
 displayed_sample_to_visible_fields=stats([x['visible']-x['sample'] for x in rows]),
 displayed_completion_to_visible_fields=stats([x['visible']-x['completed'] for x in rows]),
 render_start_to_visible_fields=stats([x['visible']-x['render_start'] for x in rows]),
 first_visible_containing_step_fields=stats([x['visible']-x['sample'] for x in containing]),
 steps_contained_in_displayed_states=containing,
 displayed_states=rows,scope='Latest completed state used by each render, joined to the same trace copper-list and four-plane DMA proof. Field-index differences only; excludes partial chains and all capture joins. Containing-step latency means the first captured displayed state at or after the step, not proof of a visible response to an input edge. Does not measure host key arrival or panel scanout, and is not a continuous capacity test.')
intervals=[]
for lo,hi in zip(sorted(boundaries),ends):
 v=[x for x in display['displayed_transition_fields'] if lo<=x<hi]
 intervals.extend(b-a for a,b in zip(v,v[1:]))
result['fields_per_displayed_frame']=stats(intervals)
result['buffer_wait']=dict(completed_waits=len(wait_polls),polls=stats([x['polls'] for x in wait_polls]) if wait_polls else None,waits_with_repeated_poll=sum(x['polls']>1 for x in wait_polls),waits_crossing_field=sum(x['end']>x['start'] for x in wait_polls),helper_cycle_fraction=wait_cycles/total_cycles if wait_cycles else None,wait_duration_fields=stats([x['end']-x['start'] for x in wait_polls]) if wait_polls else None,scope='Complete pending-buffer waits only, capture joins excluded; helper cycle fraction includes entry/exit overhead, not only polling; null means no instruction costs were recorded for this helper.')
(cap/'presentation-latency.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('displayed_states','steps_contained_in_displayed_states')},indent=2))
