#!/usr/bin/env python3
"""Same-picture live twin output gate and emulated conversion service times."""
import argparse,hashlib,json,math,statistics,struct
from pathlib import Path
from cd32_runtime import ROOT,BASE

def read(run):
    m=json.loads((run/'result.json').read_text());s=m['slave'];sy=m['symbols']
    if not m['complete'] or not m['fixture'].get('flight_verify'):raise ValueError('completed twin fixture required')
    ev=[v.split() for v in (run/'events.txt').read_text().splitlines() if not v.startswith('#')]
    ev=ev[:m['windows'][-1]['end_event']]
    if any(len(p)!=31 for p in ev) or len({p[6] for p in ev})!=1:raise ValueError('truncated or mixed-clock ledger')
    rows=[];sources=set();destinations=set();start=stop=ref=None
    for p in ev:
        pc=int(p[0],16);cycle=int(p[3]);hz=int(p[6])*64
        if pc==s+sy['flight_render_work']:
            if start is not None:raise ValueError('nested conversion')
            start=cycle;stop=ref=None
            sources.add(int(p[16],16));destinations.add(int(p[17],16))
        elif pc==s+sy['flight_render_work_done']:
            if start is None:raise ValueError('unpaired candidate')
            stop=cycle
        elif pc==s+sy['flight_reference_work']:ref=cycle
        elif pc==s+sy['flight_reference_done']:
            if not start or not stop or not ref or not start<stop<=ref<cycle:raise ValueError('unpaired twin')
            rows.append(((stop-start)/hz*1000,(cycle-ref)/hz*1000));start=None
    end=(run/'end-fast.bin').read_bytes();verified=struct.unpack_from('>I',end,s-BASE+sy['flight_verified'])[0]
    reference=struct.unpack_from('>I',end,s-BASE+sy['flight_reference'])[0]
    if not 0<reference<0x200000:raise ValueError('reference must be in CHIP, like the destination')
    history=struct.unpack_from('>I',end,s-BASE+sy['flight_history'])[0]
    if len(rows)<40 or verified<len(rows)-1 or not BASE<=history<BASE+len(end):raise ValueError('missing live twin coverage/FAST history')
    if not all(BASE<=v<BASE+len(end)-64000 for v in sources) or not all(0<v<BASE-64000 for v in destinations) or reference in destinations:
        raise ValueError("unexpected source/destination placement")
    # A final reference may have finished while its comparison is still pending.
    rows=rows[:verified]
    # First appearances populate both destination histories by full conversion.
    rows=rows[2:]
    def stats(v):return dict(count=len(v),mean_ms=statistics.mean(v),median_ms=statistics.median(v),p95_ms=sorted(v)[math.ceil(.95*len(v))-1],max_ms=max(v))
    a,b=zip(*rows)
    return dict(run=run.name,candidate=stats(a),original=stats(b),mean_time_reduction_percent=100*(1-statistics.mean(a)/statistics.mean(b)),verified_frames=verified,source_in_fast=True,destinations_in_chip=len(destinations),reference_in_chip=True,
        cpu=m['live_cpu'],fixture_sha256=m['fixture']['sha256'],emulator_sha256=m['fsuae_sha256'],
        hashes={f:hashlib.sha256((run/f).read_bytes()).hexdigest() for f in ('events.txt','end-fast.bin','result.json')})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp report required')
    rows=[read(r) for r in a.runs]
    out.write_text(json.dumps(dict(runs=rows,scope='same-picture emulated elapsed service; interrupts included; excludes limiter/display wait; twin overhead excluded from FPS claims'),indent=2)+'\n')
    for r in rows:print(r['run'],r['verified_frames'],r['candidate'],r['original'])
if __name__=='__main__':main()
