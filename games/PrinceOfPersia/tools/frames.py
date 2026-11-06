#!/usr/bin/env python3
"""Per-frame timing of a profile_run.py capture: frames.py PROF

A frame runs from the end of one frame wait (g:$1bd5a) to the end of the next; work is the
part before the wait starts (g:$1bd46); stop is the STOP blitter waits inside the work. The VBL
countdown at $49d14 is reloaded from g:$7aba (4), so a frame takes at least 4 fields (12.5 fps)."""
import collections,statistics as S,sys
from prof import load
red,meta,label=load(sys.argv[1]);FIELD=142102
ends=[(p,t) for n,p,t in red.events if n=='wait_end'];starts=[(p,t) for n,p,t in red.events if n=='wait']
frames=[]
for (e0,t0),(e1,t1) in zip(ends,ends[1:]):
    ws,wt=next(((p,t) for p,t in starts if e0<p<e1),(e1,t1))
    frames.append(dict(at=e0/FIELD,period=(e1-e0)/FIELD,work=(ws-e0)/FIELD,stop=(wt-t0)/FIELD,wait=(e1-ws)/FIELD))
n=len(red.fields);print(f'{len(frames)} frames in {n} fields: {50*len(frames)/n:.2f} fps (PAL)')
print('period histogram (fields):',sorted(collections.Counter(round(f["period"]) for f in frames).items()))
for k in ('period','work','stop','wait'):print(f"  {k:6} mean {S.mean(f[k] for f in frames):5.2f}  median {S.median(f[k] for f in frames):5.2f}  max {max(f[k] for f in frames):5.2f}")
print(f"frames whose work exceeds 4 fields: {sum(f['work']>4 for f in frames)}; without the STOP blitter waits: {sum(f['work']-f['stop']>4 for f in frames)}")
