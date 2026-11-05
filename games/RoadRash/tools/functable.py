#!/usr/bin/env python3
"""Per-function cost table from a reduced profile and a code disassembly.

  python3 tools/functable.py PROFILE.pkl.gz GAME.dis [FRAMES]

Function starts: every static jsr/bsr/jmp-absolute target in GAME.dis plus every traced call
target and the interrupt vectors' handlers. Self = cycles of PCs from a start up to the next
start. Inclusive = cycles of call stacks containing the start, with callprofile's ('irq', pc)
frames removed (on this direct game they mark resumption after an interrupt, not an entry).
Calls/frame divides executions of the start PC by FRAMES (swaps in the window)."""
import bisect,collections,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.callprofile import Reduction
r=Reduction.load(sys.argv[1]);frames=int(sys.argv[3]) if len(sys.argv)>3 else 125
starts=set()
for line in open(sys.argv[2]):
    m=re.search(r'\b(jsr|bsr\.[bw]|jmp|bsr)\s+\$([0-9a-f]+)(\.l)?$',line)
    if m:starts.add(int(m.group(2),16))
handlers={0xaea2c:'L1 SOFT (copper, once per field)',0xae9b8:'L2 CIA-A (keyboard)',0xb5ad4:'L4 audio',0xb527e:'L6 CIA-B',0xa88f2:'unused vector (rte)'}
starts|=set(handlers)
stacks=collections.Counter()
for st,c in r.stacks.items():
    stacks[tuple(f for f in st if isinstance(f,int))]+=c
for st in stacks:starts|=set(st)
starts=sorted(s for s in starts if s<0x200000)
tot=r.total();nf=len(r.fields)
selff=collections.Counter()
for pc,c in r.self.items():
    i=bisect.bisect_right(starts,pc)-1
    selff[starts[i] if i>=0 else pc]+=c
incl=collections.Counter()
for st,c in stacks.items():
    for f in set(st):incl[f]+=c
callers=collections.defaultdict(collections.Counter)
for st,c in stacks.items():
    for a,b in zip(st,st[1:]):callers[b][a]+=c
keys=sorted(set(selff)|set(incl),key=lambda k:-max(incl[k],selff[k]))
print(f'{nf} fields, {frames} frames, {tot/nf:.0f} CPU cycles/field; % of all traced CPU cycles')
print(f'{"start":>8} {"incl%":>7} {"self%":>7} {"calls/fr":>9}  caller(s)')
for k in keys:
    if max(incl[k],selff[k])/tot<0.002:continue
    cs=','.join(f'{a:x}' for a,_ in callers[k].most_common(2))
    print(f'{k:08x} {incl[k]/tot*100:7.2f} {selff[k]/tot*100:7.2f} {r.counts[k]/frames:9.1f}  {cs} {handlers.get(k,"")}')
