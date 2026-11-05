#!/usr/bin/env python3
"""Inspect the VERIFY scheduler queue and optionally count its sampled field ticks."""
import argparse, collections, json, re, struct
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto

def report(root):
    meta=json.loads((root/'anchor.json').read_text())
    mem=(root/'memory.bin').read_bytes()
    pos=mem.index(b'4DSCHED!')
    vals=struct.unpack_from('>9H2I',mem,pos+8)
    version,capacity,active,phase,rate,read,write,overflow,enqueuing,a4,ticks=vals
    assert version in (1,2) and capacity==256
    rows=[]
    for sequence in range(max(0,ticks-capacity),ticks):
        field,control,steering,analogue,pad=struct.unpack_from('>IBbBB',mem,pos+42+(sequence%capacity)*8)
        rows.append(dict(sequence=sequence,field=field,control=control,steering=steering,analogue=analogue))
    result=dict(active=active,phase=phase,rate=rate,read=read,write=write,
                backlog=(write-read)&65535,overflow=overflow,enqueuing=enqueuing,ticks=ticks,
                recorded_intervals=dict(collections.Counter(b['field']-a['field'] for a,b in zip(rows,rows[1:]))),samples=rows)
    if (root/'trace.bin').exists():
        listing=(root/'slave.lst').read_text(encoding='latin1')
        symbols={name:int(addr,16) for name,addr in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',listing,re.M)}
        base=meta['memory_base']+pos+30-symbols['sim_schedule_ticks']
        tick=re.search(r'^00:([0-9A-Fa-f]+).*addq.w #1,\$9c\(a4\)',listing,re.M)
        assert tick
        sites={base+symbols['sim_clock_interrupt']:'field_irq',base+int(tick[1],16):'published_tick',
               meta['game_base']+0x7a10:'native_timer_tick',meta['game_base']+0xe5f2:'simulation_entry'}
        trace=barto.load(root/'trace.bin')
        counts=[]
        for f in trace.fields:
            counts.append(collections.Counter(sites[pc] for pc,_,_ in trace.instructions(f) if pc in sites))
        parts=json.loads((root/'capture.json').read_text())['parts']
        split=[];offset=0
        for n in parts:
            split.append(dict(sum(counts[offset:offset+n],collections.Counter())))
            offset+=n
        result['trace']=dict(fields=len(counts),counts=dict(sum(counts,collections.Counter())),parts=split,
                irq_per_field=dict(collections.Counter(c['field_irq'] for c in counts)))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    print(json.dumps(report(p.parse_args().capture),indent=2))
