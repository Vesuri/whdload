#!/usr/bin/env python3
"""Gate for plan step A3: check_frame_log.py PROF

PROF is a profile_run.py capture of the VERIFY slave (it holds the trace and verify.bin).
Every frame-wait exit in the trace is matched to a log entry by time. Each chunk gets its own
offset, because a field runs untraced between chunks: the most common offset between trace
and log exits, with ties going to the one nearest the previous chunk's. Then the period of every frame inside one chunk must equal the
log's period to the nearest whole field. Exit 1 on any difference."""
import bisect,collections,sys
from prof import load
import frame_log
red,meta,label=load(sys.argv[1]);log=frame_log.load(sys.argv[1])
cum=[0]
for f in red.fields:cum.append(cum[-1]+f['total'])
def fld(p):
    i=bisect.bisect_right(cum,p)-1;return i+(p-cum[i])/(cum[i+1]-cum[i])
ends=[fld(p) for n,p,t in red.events if n=='wait_end']
t=0;lend=[]
for f in log:t+=f['period'];lend.append(t/frame_log.LINES)
n=bad=0;hist=collections.Counter();prev=None
for c in range(len(red.fields)//100+1):
    e=[x for x in ends if c*100<=x<(c+1)*100]
    if len(e)<2:continue
    cnt=collections.Counter(round(L-x,2) for x in e for L in lend);top=max(cnt.values())
    # Runs of equal periods tie offsets a period apart: keep the one nearest the last chunk's.
    off=min((o for o,k in cnt.items() if k==top),key=lambda o:abs(o-prev) if prev is not None else 0)
    prev=off
    idx=[min(range(len(lend)),key=lambda j:abs(lend[j]-x-off)) for x in e]
    for (a,ia),(b,ib) in zip(zip(e,idx),zip(e[1:],idx[1:])):
        if abs(lend[ib]-b-off)>0.05 or ib!=ia+1:print('unmatched exit near field',round(b,2));bad+=1;continue
        n+=1;lp=round(log[ib]['period']/frame_log.LINES);hist[lp]+=1
        if round(b-a)!=lp:print(f'step {log[ib]["step"]}: trace {b-a:.2f} fields, log {lp}');bad+=1
print(f'{n} frames compared, {bad} differ; log periods {sorted(hist.items())}')
sys.exit(1 if bad else 0)
