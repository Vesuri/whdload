#!/usr/bin/env python3
"""Completed-call and inner-loop costs for W3–W6; boundary-partial calls are excluded."""
import argparse, os, re, statistics
from pathlib import Path
import barto
from lov_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--base',type=lambda x:int(x,0),default=0xc00000)
a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
b=(a.capture/'code.bin').read_bytes();t=barto.load(str(a.capture/'trace.bin'))
r={n:(lo,hi) for lo,hi,n,o in regions(b,a.base,t.chip)};h=r['h12'][0]
entries={h+0x27bc:'render',h+0x4c1a:'wall columns',h+0x4cbe:'wall columns',
         h+0x4d42:'wall columns',h+0x51a2:'sky/floor clear',h+0x51ee:'clear inner',
         h+0x5114:'sprite draws',h+0x93bc:'mapped sprite draws',
         h+0x517e:'sprite inner columns',h+0x9452:'mapped sprite inner columns',
         h+0x94e2:'mapped sprite inner columns',h+0x2998:'ray reciprocal',h+0x2de4:'ray reciprocal',h+0x3236:'ray reciprocal',h+0x3676:'ray reciprocal',h+0x3ab4:'ray reciprocal',h+0x3f0c:'ray reciprocal',h+0x435e:'ray reciprocal',h+0x479c:'ray reciprocal'}
ends={h+0x5192:'sprite inner columns',h+0x9468:'mapped sprite inner columns',
      h+0x94f8:'mapped sprite inner columns',h+0x29aa:'ray reciprocal',h+0x2df6:'ray reciprocal',h+0x3248:'ray reciprocal',h+0x3688:'ray reciprocal',h+0x3ac6:'ray reciprocal',h+0x3f1e:'ray reciprocal',h+0x4370:'ray reciprocal',h+0x47ae:'ray reciprocal'}
returns=set()
for name in ('h12','slave'):
    lo,hi=r[name];blob=b[lo-a.base:hi-a.base]
    returns.update(lo+i for i in range(0,len(blob)-1,2) if blob[i:i+2]==b'\x4e\x75')
# Count actual texel rows examined, including transparent pixels. Patched hook JMPs
# are not rows; the replacement's fixed-displacement row labels are.
rows={h+o for o in (0x517e,0x9452,0x94e2) if b[h+o-a.base:h+o-a.base+2]==b'\x30\x1d'}
lst=(a.capture/'slave.lst').read_text(errors='replace')
rows.update(r['slave'][0]+int(o,16) for o in re.findall(r'^_w4_row_\d_\d\s+00:([0-9A-F]{8})\s*$',lst,re.M))
cache_paths={}
for name in ("hit", "miss"):
    match=re.search(r"^_w5_cache_"+name+r"\s+00:([0-9A-F]{8})\s*(?:EXP)?\s*$",lst,re.M)
    if match:cache_paths[r["slave"][0]+int(match[1],16)]=name
cache_counts={"hit":0,"miss":0}
active={};calls={name:[] for name in set(entries.values())}
for field in t.fields:
    for pc,cost,regs in t.instructions(field):
        if pc in cache_paths:cache_counts[cache_paths[pc]]+=1
        # Original inner-loop entries repeat for each row, while patched entries
        # run once per column. Only an inactive scope starts a new completed call.
        if pc in entries and entries[pc] not in active:
            active[entries[pc]]=[regs[15],0,0,0]
        # End labels belong to the unchanged column tail, excluded on both sides.
        if pc in ends and ends[pc] in active and regs[15]==active[ends[pc]][0]:
            name=ends[pc];calls[name].append(active.pop(name)[1:])
        for name,sample in active.items():
            sample[1]+=cost
            if abs(regs[15]-sample[0])<0x10000:sample[2]+=cost
            if pc in rows and 'sprite inner columns' in name:sample[3]+=1
        if pc in returns:
            for name in list(active):
                if regs[15]==active[name][0]:calls[name].append(active.pop(name)[1:])
for name in ('render','wall columns','sprite draws','mapped sprite draws','sprite inner columns',
             'mapped sprite inner columns','ray reciprocal','sky/floor clear','clear inner'):
    samples=calls[name]
    if not samples:print(f'{name}: no completed calls');continue
    inc,main,pixels=zip(*samples)
    line=f'{name}: {len(samples)} complete calls; inclusive {statistics.mean(inc):.0f}, main-task {statistics.mean(main):.0f} cycles/call'
    if sum(pixels):line+=f'; {sum(main)/sum(pixels):.2f} main-task cycles/scanned pixel ({sum(pixels)} pixels)'
    print(line)

if sum(cache_counts.values()):
    total=sum(cache_counts.values())
    print("ray cache: {hit} hits, {miss} misses; {rate:.1f}% hit rate".format(
        **cache_counts, rate=100*cache_counts["hit"]/total))
