#!/usr/bin/env python3
"""Verify saved ordinary-runtime lifecycle evidence, without an emulator."""
import json,struct,hashlib
from pathlib import Path
root=Path('tmp/lifecycle-runtime-67');meta=json.loads((root/'start/anchor.json').read_text());a=meta['data_base']+0x7ffe-meta['memory_base']
load=lambda n:json.loads((root/(n+'.json')).read_text())
raw=lambda n:(root/(n+'.bin')).read_bytes()
def block(b,marker,size):
    p=b.index(marker)+12;assert struct.unpack_from('>H',b,p-2)[0]==size,(marker,size);return b[p:p+size]
def semantic(b):
    out=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]+block(b,b'4DA4PHYS',152)+block(b,b'4DTSTATE',32)+block(b,b'4DAUXPHY',192)+block(b,b'4DCAM050',8)
    assert len(out)==1510;return out
p,q=load('pause-window-start'),load('pause-window-end')
assert q['sim_clock_fields']-p['sim_clock_fields']==250
assert q['sim_schedule_modal_fields']-p['sim_schedule_modal_fields']==250
for k in ('sim_schedule_ticks','consumer','imported','sim_schedule_read','sim_schedule_write','queue','sim_schedule_phase','player','opponent','private_sha256'):assert p[k]==q[k],k
assert p['sim_schedule_modal']==q['sim_schedule_modal']==1
assert semantic(raw('pause-window-start'))==semantic(raw('pause-window-end'))
r=load('resume-trace');start,end=r['start'],r['end'];rows=r['fields'];bodies=r['bodies']
assert [b[1] for b in bodies]==list(range(start['consumer']+1,end['consumer']+1))
assert len(bodies)==249 and all(b[2]==0 for b in bodies)
assert end['sim_schedule_ticks']-start['sim_schedule_ticks']==250
assert end['sim_schedule_modal_resumes']-start['sim_schedule_modal_resumes']==1
assert end['sim_schedule_modal_dropped']-start['sim_schedule_modal_dropped']==start['queue']==2
assert end['sim_schedule_read']-start['sim_schedule_read']==len(bodies)+2
assert end['queue']==1 and end['sim_schedule_modal']==0
assert [f[2] for f in rows]==list(range(start['sim_schedule_ticks']+1,end['sim_schedule_ticks']+1))
assert all(f[1]==sum(b[0]<f[0] for b in bodies) for f in rows)
assert all(f[5]==0 for f in rows)
restart=load('restart-bounded');assert 'RESTART_HIT 1' in (root/'restart-bounded-log.txt').read_text()
assert (restart['consumer'],restart['started'],restart['player']['speed'])==(0,0,0)
assert restart['player']['position']==[493824,512,347008]
assert block(raw('restart-bounded'),b'4DA4PHYS',152)==bytes(152)
assert [restart[k] for k in ('selected','active_rate','recorded_rate')]==[50]*3
restored=raw('rewind-restored');hist=restored.index(b'4DHISTRY');record_size=struct.unpack_from('>H',restored,hist+12)[0];assert record_size==392
saved=hist+28;assert struct.unpack_from('>H',restored,saved)[0]==50
native=struct.unpack_from('>I',restored,a-0x16bc)[0]-meta['memory_base']
expected=restored[native:native+1120]+restored[saved+2:saved+record_size]
assert semantic(restored)==expected
live,replayed=semantic(raw('live-200')),semantic(raw('replay-200'))
assert live==replayed
for name,mode in [('live-200',0),('replay-200',2)]:
    state=load(name);assert state['consumer']==200 and state['mode']==mode
x,y=load('replay-end'),load('replay-end-held')
assert y['sim_clock_fields']-x['sim_clock_fields']==250
for k in ('sim_schedule_ticks','consumer','imported','sim_schedule_read','sim_schedule_write','queue'):assert x[k]==y[k],k
assert x['consumer']==x['imported']==202 and x['queue']==0 and x['sim_schedule_active']==3
assert struct.unpack_from('>H',raw('replay-end'),a-0x1738)[0]==202
assert semantic(raw('replay-end'))==semantic(raw('replay-end-held'))
for name in ('pause-window-start','pause-window-end','resume-end','restart-bounded','replay-200','replay-end-held'):
    state=load(name);assert state['sim_schedule_overflow']==state['perf_failure']==0
report=dict(runtime_sha256=hashlib.sha256((root/'start/slave.slave').read_bytes()).hexdigest(),emulator_sha256=hashlib.sha256(Path(json.loads((root/'launch.json').read_text())['settings']['FSUAE']).read_bytes()).hexdigest(),pause_fields=250,paused_semantic_bytes_equal=1510,resume_fields=250,resume_published=250,resume_completed=249,resume_discarded_private_inputs=2,resume_controls_all_released=True,maximum_resume_queue=max((f[4]-f[3])&65535 for f in rows),restart_preserves_a4000=True,restart_private_zero_bytes=152,checkpoint_zero_restored_bytes=1510,replayed_tick=200,replayed_equal_bytes=1510,live_state_sha256=hashlib.sha256(live).hexdigest(),replay_end_tick=202,replay_end_held_fields=250,replay_end_equal_bytes=1510,scope='Current ordinary runtime; native input.device keyboard route, FULL/solo/C2=1, configured04025MHz,2MBchip4MBfast,PAL,WARP1. No game RAM writes or VERIFY fixtures. Keyboard rewind visited checkpoint0; subsequent navigation had reconstructed to198 before final Play request. Exact tick200 comparison proves this native UI seek/play path, not200 paced playback steps fromzero. No disk replay, nonzero checkpoint, all lifecycle, hardware capacity or handling claim.')
(root/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
