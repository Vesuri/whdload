#!/usr/bin/env python3
"""Continuous window from a paused quick_start anchor, timed by the native CIAB clock.
Counts render-loop iterations (VERIFY tape frame counter) and consumed simulation steps.
Usage: measure_window.py CAPTURE [--seconds 5]"""
import argparse,json,re,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from profile_window import command
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--seconds',type=float,default=5.0);a=p.parse_args()
cap=a.capture.resolve();m=json.loads((cap/'anchor.json').read_text())
game=m['game_base'];a4=m['data_base']+0x7ffe;frames_addr=m.get('marker',0)+16
native=m.get('native_frame_counter',False)
ECLK=709379
def rd():
 q={'frames':('$bench_native_frames' if native else f'*(unsigned int *){frames_addr:#x}'),'consumed':f'*(unsigned short *){a4-0x940:#x}','produced':f'*(unsigned short *){a4+0xa0:#x}',
    'clock':f'*(unsigned int *){a4+0x2342:#x}','latch':f'*(unsigned short *){a4-0x217c:#x}','rate':f'*(unsigned short *){a4-0x15fa:#x}',
    'detail':f'*(unsigned char *){a4-0x7708:#x}','mode':f'*(unsigned char *){a4+0x45:#x}','race_base':f'*(unsigned short *){a4-0x2e0:#x}'}
 for n,addr in m.get('clock_symbols',{}).items():q[n]=f'*(unsigned '+('int' if n in ('sim_clock_fields','sim_schedule_ticks','perf_failure') else 'short')+f' *){addr:#x}'
 out=command('gdb '+'\n'.join(f'p /u {v}' for v in q.values()))
 vals=[int(x) for x in re.findall(r'^\$\d+ = (\d+)',out,re.M)];assert len(vals)==len(q),out
 return dict(zip(q,vals))
s=rd();ECLK=715909 if s.get('sim_time_field_hz')==60 else 709379;hz=ECLK/s['latch'];K=round(a.seconds*hz)
script=['delete','set $bench_swaps=0',f'break *{game+0x35332:#x}','commands','silent','set $bench_swaps=$bench_swaps+1','continue','end',f'tbreak *{game+0x36e0e:#x} if *(unsigned int *){a4+0x2342:#x}>={s["clock"]+K}','continue','printf "BENCH_SWAPS %u\\n", $bench_swaps','info registers pc','delete']
if native:
 script[2:2]=[f'break *{game+0x7500:#x}','commands','silent','set $bench_native_frames=$bench_native_frames+1','continue','end']
if os.environ.get('BENCH_PRIMITIVES')=='1':
 extras=[]
 for name,off in [('circle',0x286fe),('wheel',0x28c08),('dot',0x333b2)]:
  extras += [f'set $p3_{name}=0',f'break *{game+off:#x}','commands','silent',f'set $p3_{name}=$p3_{name}+1','continue','end']
 script[1:1]=extras
r=command('gdb '+'\n'.join(script))
(cap/'bench-window.log').write_text(r)
swaps=int(re.search(r'BENCH_SWAPS (\d+)',r)[1])
assert f'{game+0x36e0e:x}' in r, r
e=rd();sec=(e['clock']-s['clock'])*s['latch']/ECLK
res=dict(start=s,end=e,timer_hz=hz,latch_changed=s['latch']!=e['latch'],emulated_seconds=sec,
 render_iterations=e['frames']-s['frames'],consumed_steps=(e['consumed']-s['consumed'])&0xffff,produced_steps=(e['produced']-s['produced'])&0xffff)
res['render_loop_fps']=res['render_iterations']/sec;res['copper_switches']=swaps;res['fps']=swaps/sec;res['steps_per_second']=res['consumed_steps']/sec;res['produced_per_second']=res['produced_steps']/sec
res['backlog_start']=(s['produced']-s['consumed'])&0xffff;res['backlog_end']=(e['produced']-e['consumed'])&0xffff
res['race_clock_ratio_from_consumed_ticks']=res['consumed_steps']/s['rate']/sec
res['race_clock_ratio']=(((e['race_base']+e['consumed'])-(s['race_base']+s['consumed']))&65535)/s['rate']/sec
res['race_clock_basis']='Original elapsed-time formatter input: history base + consumed steps, divided by native rate'
if 'sim_schedule_write' in s:
 res['queue_start']=(s['sim_schedule_write']-s['sim_schedule_read'])&65535
 res['queue_end']=(e['sim_schedule_write']-e['sim_schedule_read'])&65535
 assert e['sim_schedule_overflow']==e['perf_failure']==0
res['timing_basis']='CIA E-clock/latch; '+('NTSC' if ECLK==715909 else 'PAL')+'; rejects latch changes'
assert not res['latch_changed']
if os.environ.get('BENCH_PRIMITIVES')=='1':
 text=command('gdb '+ '\n'.join(f'p /u $p3_{name}' for name in ('circle','wheel','dot')))
 vals=[int(x) for x in re.findall(r'^\$\d+ = (\d+)',text,re.M)]
 assert len(vals)==3,text
 res['native_primitive_calls']=dict(zip(('circle','wheel','dot'),vals))
(cap/'window.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
