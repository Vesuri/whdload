#!/usr/bin/env python3
"""Phase-9 elapsed-clock acceptance and equal-world-time state comparisons."""
import argparse,hashlib,json,struct
from pathlib import Path
from cd32_runtime import BASE,ROOT
from flight_report import HZ,SIZE,STATE_RANGES
from simulation_capture import cpu

def read(run):
    m=json.loads((run/'result.json').read_text());h=m['hunks'][0];s=m['slave'];sy=m['symbols']
    if not m['complete'] or m['off']:raise ValueError('completed enabled capture required')
    ev=[]
    for line in (run/'events.txt').read_text().splitlines():
        if line.startswith('#'):continue
        p=line.split()
        if len(p)!=31:raise ValueError('truncated observer row')
        ev.append(dict(pc=int(p[0],16),cycles=int(p[3]),field=int(p[1]),sp=int(p[23],16)))
    selected=[w for w in m['windows'] if w['name'].startswith('window-')][2:]
    if not selected:raise ValueError('warmup plus measured windows required')
    a,b=selected[0]['first_event'],selected[-1]['end_event'];ee=ev[a:b]
    vb=[e for e in ee if e['pc']==h+0x34162];done=[e for e in ee if e['pc']==s+sy['timing_world_done']]
    if len(done)<200:raise ValueError('at least 200 measured completed updates required')
    field_hz=(len(vb)-1)*HZ/(vb[-1]['cycles']-vb[0]['cycles'])
    elapsed=(vb[-1]['cycles']-vb[0]['cycles'])/HZ
    # Count over the same closed VBL interval, not profiler labels or host time.
    counted=sum(vb[0]['cycles']<=q['cycles']<vb[-1]['cycles'] for q in done)
    rate=counted/elapsed
    end=(run/'end-fast.bin').read_bytes()
    def val(name,fmt='I'):return struct.unpack_from('>'+fmt,end,s-BASE+sy[name])[0]
    if m['fixture'].get('timing_verify') and val('timing_verify_schedule','H')!={'normal':0,'slow':10,'one-field':1}[m['schedule']]:raise ValueError('live diagnostic schedule mismatch')
    observed=val('timing_hz');clock=struct.unpack_from('>6IH',end,s-BASE+sy['timing_clock'])
    if observed not in (50,60) or abs(field_hz/observed-1)>.01:raise ValueError('beam classification/observed cadence mismatch')
    if abs(rate/10-1)>.01:raise ValueError(f'{run.name}: world clock outside 1%: {rate}')
    if val('timing_input_overflows'):raise ValueError('input-history overflow in fitting schedule')
    snapshot_pc=h+(0x3378e if m['presentation_states'] else 0x2da)
    se=[(i,e) for i,e in enumerate(ev) if e['pc']==snapshot_pc]
    raw=(run/'states.bin').read_bytes()
    if len(raw)!=len(se)*SIZE:raise ValueError('state snapshot/event mismatch')
    states={};responsive=0;between=0
    last=None
    for n,(i,e) in enumerate(se):
        if not a<=i<b:continue
        state=raw[n*SIZE:(n+1)*SIZE];tick=struct.unpack_from('>H',state,0x914c)[0]
        if last and last[0]==tick:
            between+=1
            if state[0xa148:0xa154]!=last[1][0xa148:0xa154]:responsive+=1
            # Responsive orientation may change; world positions may not.
            if state[0x919a:0x919a+61*12]!=last[1][0x919a:0x919a+61*12]:raise ValueError('positions changed between updates')
        states[tick]=state;last=(tick,state)
    pauses=[]
    for w in m['windows']:
        if w['name']!='pause':continue
        if any(e['pc']==s+sy['timing_world_done'] for e in ev[w['first_event']:w['end_event']]):raise ValueError('world advanced while paused')
        before=(run/'pause-start.bin').read_bytes();after=(run/'pause-end.bin').read_bytes();d=m['hunks'][1]-BASE
        same={k:before[d+o:d+o+n]==after[d+o:d+o+n] for k,(o,n) in STATE_RANGES.items()}
        if not all(v for k,v in same.items() if k!='draw_counter'):raise ValueError('paused world state changed')
        pauses.append(dict(fields=w['fields'],world_unchanged=True))
    result=dict(run=run.name,schedule=m['schedule'],cpu=cpu(m['live_cpu']),ntsc=m['ntsc'],field_hz=field_hz,clock_hz=observed,
        elapsed_seconds=elapsed,completed_ticks=counted,world_hz=rate,error_percent=(rate/10-1)*100,clock=list(clock),
        input_overflows=val('timing_input_overflows'),dropped_active_fields=val('timing_input_dropped_fields'),
        pauses=pauses,between_tick_publications=between,responsive_publications=responsive,
        hashes={f:hashlib.sha256((run/f).read_bytes()).hexdigest() for f in ('result.json','events.txt','states.bin')})
    return result,states,m

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp report required')
    rows=[];reference=None;comparisons=[]
    for run in a.runs:
        result,states,meta=read(run);rows.append(result)
        if not meta['presentation_states']:
            if reference is None:reference=(run.name,states,meta)
            else:
                name,prior,pm=reference
                common=sorted(set(prior)&set(states))
                ranges={k:sum(states[t][o:o+n]!=prior[t][o:o+n] for t in common) for k,(o,n) in STATE_RANGES.items()}
                displacement=max((max(abs(x-y) for x,y in zip(struct.unpack_from('>3i',states[t],0x919a),struct.unpack_from('>3i',prior[t],0x919a))) for t in common),default=0)
                comparisons.append(dict(reference=name,run=run.name,matched_ticks=len(common),same_held_key=meta['held_key']==pm['held_key'],different_ticks_per_range=ranges,max_player_position_difference_fixed8=displacement))
        print(f"{run.name}: {result['world_hz']:.5f} updates/s ({result['error_percent']:+.3f}%), fields {result['field_hz']:.5f} Hz")
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(runs=rows,comparisons=comparisons,scope='emulated elapsed clock; no exclusive CPU/DMA or physical hardware claims'),indent=2)+'\n')
if __name__=='__main__':main()
