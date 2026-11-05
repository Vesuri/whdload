#!/usr/bin/env python3
"""Summarize separately validated runtime presentation and capacity windows."""
import argparse, collections, hashlib, json, struct
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
a=p.parse_args();cap=a.capture
load=lambda name:json.loads((cap/name).read_text())
m=load('anchor.json');assert m['standalone_runtime']
l=load('presentation-latency.json');d=load('display-check.json');c=load('capacity.json')
sha=hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest()
assert sha==c['slave_sha256']==load('launch.json')['slave_sha256']
assert l['fields']==d['fields']==c['fields']==250
assert l['capture_part_starts']==d['capture_part_starts']
assert l['input_publications']==250
b=(cap/'memory.bin').read_bytes();aa=m['data_base']+0x7ffe-m['memory_base']
profile=dict(detail=b[aa-0x7708],opponent=b[aa-0x174a],started=b[aa-0x68b],rate=struct.unpack_from('>H',b,aa-0x15fa)[0],mode=b[aa+0x45],tick=struct.unpack_from('>H',b,aa-0x940)[0])
assert profile['started']==1 and profile['rate']==50 and profile['mode']==0,profile
for edge in ('start','end'):
 assert c[edge]['detail']==profile['detail'] and c[edge]['opponent']==profile['opponent']
 assert c[edge]['failure']==c[edge]['overflow']==0
assert c['steady_tick_continuity'] and not c['lifecycle_observation']
assert c['produced']==250
if profile['opponent']:
 assert c['opponent_calls']==c['completed'],'missing opponent updates'
 assert c['start']['cars']['opponent']['position']!=c['end']['cars']['opponent']['position'],'opponent did not move'
else:assert c['opponent_calls']==0
q=[(row[3]-row[4])&65535 for row in c['rows']]
counts=[c['rows'][0][1]]+[y[1]-x[1] for x,y in zip(c['rows'],c['rows'][1:])]
r=dict(slave_sha256=sha,profile_state=profile,profile_fields=l['fields'],profile_parts=l['capture_part_starts'],publications=l['input_publications'],physics_latency_fields=l['sample_to_completion_fields'],containing_state_latency_fields=l['first_visible_containing_step_fields'],display_fps=d['validated_fps_within_contiguous_parts'],continuous_capacity_fields=c['fields'],continuous_completed=c['completed'],continuous_produced=c['produced'],completion_debt_change=c['completion_debt_change'],queue_start=c['start']['queue'],queue_end=c['end']['queue'],queue_min=min(q),queue_max=max(q),completion_per_field_histogram=dict(collections.Counter(counts)),opponent_calls=c['opponent_calls'],scope='Ordinary runtime; held throttle. Separate profile and continuous capacity windows, not matched workloads across graphics levels. No physical-key edge, pixel-response, hardware or worst-case proof. See launch.json for configured CPU/memory/rendering settings.')
(cap/'validation.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
