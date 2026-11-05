#!/usr/bin/env python3
"""Frame count of flight_profile's window without tracing: fps.py OUT

Replays the route and the window (same keys on the same fields), reading the buffer index
D+4BB0 (flips once per frame at the swap +04496) after every field. Works on CPUs whose trace
is empty (68030+). Assumes at most one swap per field. Saves start.png/end.png and
OUT/frames.txt (per-field flip flags). Data hunk base from MEMDIR layout (a500/a1200-fast: $9951F8).
"""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from gunship import Session
from route import run
from flight_profile import ROUTE,window
# Refocus comparison: use the same existing buffer-swap observation on both paths.
if os.environ.get('REFOCUS') == '1':
    import json, hashlib, statistics, struct
    from pathlib import Path
    from layout import locate
    from gunship import machine
    custom=int(os.environ.get('CUSTOM1','0'))
    s=Session(sys.argv[1],dict(NTSC='0', EXTRA_ARGS=machine().get('EXTRA_ARGS','')+' --video_driver=null', WHD_ARGS=f'CUSTOM1={custom} CUSTOM2=12345'))
    try:
        run(s,ROUTE)
        mem=s.read(0x200000,0x800000); L=locate(mem); h=L['hunks']
        (s.out/'layout.json').write_text(json.dumps(L))
        markers=[];pos=0
        while True:
            pos=mem.find(b'GSVFY001',pos)
            if pos<0:break
            words=struct.unpack_from('>15I',mem,pos+8)
            if words[0]==h[0] and words[13] and words[14]==8192:markers.append((0x200000+pos,words[13]))
            pos+=8
        assert len(markers)==1,markers
        marker,log=markers[0]
        def log_count():return int.from_bytes(s.read(marker+44,4),'big')
        first_count=log_count()
        def sample():
            player=s.read(h[6]+0x3b88,0x56)
            return dict(field=int.from_bytes(s.read(h[2]+0x1c,4),'big'),
                tick=int.from_bytes(player[12:14],'big'),
                buffer=int.from_bytes(s.read(h[6]+0x4bb0,2),'big'),player=player.hex())
        initial=sample(); rows=[];events=[]
        def chunk(n):
            assert n%2==0
            for _ in range(n//2):
                s.fields(1); rows.append(sample())
        # Same takeoff keys as flight_profile.window; use existing frame-probe stick pulses.
        for i in range(10):
            s.key('f1',1); chunk(4); s.key('f1',0); chunk(6)
        for event in ['JOY2_LEFT','JOY2_RIGHT']*4:
            events.append(dict(event=event,field=rows[-1]['field']))
            s.cmd(f'monitor input {event} 1');chunk(6)
            s.cmd(f'monitor input {event} 0');chunk(40)
        chunk(32)
        count=log_count()
        logged=list(struct.iter_unpack('>IHH',s.read(log,count*8)))
        flips=[r[0] for r in logged[first_count:]]
        (s.out/'frame-log.json').write_text(json.dumps(logged))
        (s.out/'samples.json').write_text(json.dumps(dict(initial=initial,rows=rows)))
        for event in events:
            event['next_completed_field']=next((f for f in flips if f>event['field']),None)
            event['delay_ms']=20*(event['next_completed_field']-event['field']) if event['next_completed_field'] else None
        span=rows[-1]['field']-initial['field'];ticks=(rows[-1]['tick']-initial['tick'])&65535
        assert span==500,(span,initial,rows[-1])
        slave=Path(os.environ['SLAVE'])
        result=dict(machine=os.environ['MACHINE'],custom1=custom,video='PAL',fields=span,seconds=span/50,
            completed_frames=len(flips),fps=len(flips)*50/span,world_ticks=ticks,world_hz=ticks*50/span,
            input_to_next_frame_ms=[e['delay_ms'] for e in events],events=events,flips=flips,
            slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),
            scope='Normal startup, 500-field takeoff window, existing VERIFY completed-swap log; native state sampled every two fields. Delay is injected stick input to next completed frame, not proof that frame contains input or scanout latency.')
        assert hashlib.sha256((s.run/'dh1/Gunship.slave').read_bytes()).hexdigest()==result['slave_sha256']
        (s.out/'samples.json').write_text(json.dumps(dict(initial=initial,rows=rows)))
        (s.out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
        s.shot('end.png');print(json.dumps(result),flush=True)
    finally:s.quit()
    sys.exit(0)
BUF=0x9951f8+0x4bb0
out=sys.argv[1];s=Session(out);flips=[]
def rd():return s.read(BUF,2)
try:
    run(s,ROUTE);s.shot('start.png');last=[rd()]
    def chunk(n):
        for i in range(n):
            s.fields(1);v=rd();flips.append(int(v!=last[0]));last[0]=v
    window(s,chunk);s.shot('end.png')
    (s.out/'frames.txt').write_text(''.join(map(str,flips))+'\n')
    print(f'{os.environ.get("AMIGA_SETUP")}: {sum(flips)} frames in {len(flips)} fields = {50*sum(flips)/len(flips):.1f} fps')
finally:s.quit()
