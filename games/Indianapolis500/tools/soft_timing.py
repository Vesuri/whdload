#!/usr/bin/env python3
"""Time the parts of each SOFT (simulation tick) with a SOFT_TIMING build; read-only.
  soft_timing.py TICKS OUTDIR CODE.bin BASE      (TICKS <= 256, from the current point on)
Parts: input = entry..game:00bf8 (driving only), player = game:00bf8..03138,
publish = 03138..field update, field = game:020d26, tail = rest to the exit (game:03af0).
Times include the higher-level interrupts (CIA, VBL, blitter) that preempt SOFT.
"""
import argparse,json,struct,statistics,tempfile
from pathlib import Path
from state_fields import command
from i500_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('ticks',type=int);p.add_argument('out',type=Path)
p.add_argument('dump',type=Path);p.add_argument('base',type=lambda s:int(s,0));a=p.parse_args()
RING,SIZE,LATCH,ECLOCK=256,44,11883,709379
assert 1<=a.ticks<=RING
b=a.dump.read_bytes();rr={n:(lo,hi) for lo,hi,n,o in regions(b,a.base)}
lo,hi=rr['slave'];m=b.find(b'I5ST',lo-a.base,hi-a.base);assert m>=0,'SOFT_TIMING build required'
magic=a.base+m;done=magic+struct.unpack_from('>H',b,m+4)[0];count=magic+6;samples=magic+16
a.out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='i500-soft-') as temp:
    reply=command(f'''printf "SOFT start %u\\n", *(unsigned int *){count:#x}
set $i500_end = *(unsigned int *){count:#x} + {a.ticks}
break *{done:#x}
while *(unsigned int *){count:#x} < $i500_end
continue
end
delete
printf "SOFT end %u\\n", *(unsigned int *){count:#x}
dump binary memory {temp}/ring.bin {samples:#x} {samples+RING*SIZE:#x}
''')
    (a.out/'gdb.txt').write_text(reply)
    ring=(Path(temp)/'ring.bin').read_bytes()
start=int(reply.split('SOFT start ')[1].split()[0]);end=int(reply.split('SOFT end ')[1].split()[0])
assert end==start+a.ticks,(start,end)
rows=[]
for n in range(start,end):
    o=(n%RING)*SIZE;stamps=[]
    for slot in range(6):
        clock,timer=struct.unpack_from('>IH',ring,o+slot*6)
        stamps.append(None if clock==0xffffffff else clock*LATCH+(LATCH-timer))
    mode,style,flags=ring[o+36],ring[o+37],ring[o+38];event=struct.unpack_from('>H',ring,o+40)[0]
    rows.append(dict(soft=n,stamps=stamps,mode=mode,style=style,flags=flags,event=event))
ms=lambda units:units*1000/ECLOCK
parts=dict(input=(0,1),player=(1,2),publish=(2,3),field=(3,4),tail=(4,5),total=(0,5))
for r in rows:
    s=r['stamps'];r['ms']={}
    for name,(x,y) in parts.items():
        if s[x] is not None and s[y] is not None:r['ms'][name]=ms(s[y]-s[x])
    if s[1] is None and s[0] is not None and s[2] is not None:r['ms']['director']=ms(s[2]-s[0])
for previous,r in zip(rows,rows[1:]):
    if previous['stamps'][0] is not None and r['stamps'][0] is not None:
        r['ms']['period']=ms(r['stamps'][0]-previous['stamps'][0])
# A stamp read while the CIA reload is pending is off by one tick; flag rather than hide it.
suspect=[r['soft'] for r in rows if any(v<0 or v>60 for k,v in r['ms'].items() if k!='period')]
summary={}
for name in [*parts,'director','period']:
    v=[r['ms'][name] for r in rows if name in r['ms'] and r['soft'] not in suspect]
    if v:summary[name]=dict(samples=len(v),median=statistics.median(v),mean=statistics.mean(v),
                             minimum=min(v),maximum=max(v),p90=sorted(v)[int(0.9*(len(v)-1))])
modes=sorted({(r['mode'],r['event'],r['style'],r['flags']) for r in rows})
result=dict(ticks=a.ticks,first_soft=start,modes=modes,suspect=suspect,summary=summary,rows=rows)
(a.out/'soft.json').write_text(json.dumps(result,indent=1)+'\n')
print(f'{a.ticks} SOFTs from #{start}; (mode, event, style, 9b2e) {modes}; suspect {len(suspect)}')
for name,s in summary.items():
    print(f"{name:8} median {s['median']:6.2f} ms  mean {s['mean']:6.2f}  p90 {s['p90']:6.2f}  "
          f"min {s['minimum']:6.2f}  max {s['maximum']:6.2f}  (n={s['samples']})")
