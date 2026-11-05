#!/usr/bin/env python3
"""Validate the phase 3 SWAP_ONLY ledger against full traces and repeat boots."""
import argparse, json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from PIL import Image


def read_events(path):
    events=[]
    for line in path.read_text().splitlines():
        if line.startswith('#'): continue
        words=line.split()
        if len(words)!=31: raise ValueError('truncated observer record')
        row=[int(w,16 if i==0 or 8<=i<24 else 10) for i,w in enumerate(words)]
        events.append(row)
    if any(e[7]!=128 for e in events):raise ValueError('unexpected CPU cycle unit')
    if not events: raise ValueError('empty observer ledger')
    if any(b[3]<a[3] or b[1]<a[1] for a,b in zip(events,events[1:])): raise ValueError('nonmonotonic clock')
    return events


def run_events(run, meta):
    events=read_events(run/'events.txt')
    # The measured window ends at the first menu-ready instruction. The owned
    # process can briefly resume on debugger disconnect; that shutdown is outside
    # the window, as is the subsequent one-field menu screenshot.
    end=next((i for i,e in enumerate(events) if e[0]==meta['hunks'][0]+0x20214),None)
    if end is None:raise ValueError('menu endpoint missing')
    return events[:end+1]


def validate_trace(path, events, h0):
    watch={h0+x for x in (0x3378e,0x3379a,0x33ce2,0x34162)}
    trace=barto.load(str(path)); observed=[e for e in events if e[0] in watch]
    records=[]; pcs=0
    for field in trace.fields:
        for pc,cost,regs in trace.instructions(field):
            if pc not in (None,0x7fffffff): pcs+=1
            if pc in watch: records.append((pc,field.index,tuple(regs[:16])))
    if pcs<100 or not records: raise ValueError('missing instruction PCs/coverage')
    signature=lambda e:(e[0],tuple(e[8:24]))
    first=(records[0][0],records[0][2])
    starts=[i for i,e in enumerate(observed) if signature(e)==first]
    matches=[]
    for start in starts:
        chunk=observed[start:start+len(records)]
        if len(chunk)!=len(records):continue
        if all(signature(e)==(r[0],r[2]) for e,r in zip(chunk,records)):
            offsets={e[1]-r[1] for e,r in zip(chunk,records)}
            if len(offsets)==1: matches.append((chunk,offsets.pop()))
    if len(matches)!=1: raise ValueError('trace/observer PC, register or field disagreement')
    chunk,base=matches[0]
    # Check every observed event in the complete traced fields, including edges.
    entire=[e for e in observed if base<=e[1]<base+len(trace.fields)]
    if entire!=chunk: raise ValueError('trace lost an edge event')
    counts={hex(pc-h0):[sum(r[0]==pc and r[1]==f.index for r in records) for f in trace.fields] for pc in watch}
    if counts['0x34162'] != [1]*len(trace.fields): raise ValueError('VBL counter is not one per physical field')
    if not sum(counts['0x3378e']): raise ValueError('no publications in validation window')
    if counts['0x3378e']!=counts['0x3379a'] or counts['0x3378e']!=counts['0x33ce2']:
        raise ValueError('publication/COP2LC accounting differs')
    return dict(fields=len(trace.fields),instruction_records=pcs,field_base=base,counts=counts,pass_=True)


def compare(a,b):
    ma,mb=[json.loads((x/'result.json').read_text()) for x in (a,b)]
    if ma!=mb or not ma['complete']:raise ValueError('run configurations or milestones differ')
    ea,eb=[run_events(x,ma) for x in (a,b)]
    if ea!=eb: raise ValueError('raw event/clock/music/register ledgers differ')
    for name in ma['milestones']:
        x,y=[Image.open(p/(name+'.png')).convert('RGB') for p in (a,b)]
        if x.size!=y.size or x.tobytes()!=y.tobytes():raise ValueError('picture differs: '+name)
        # All allocated live game hunks, not WHDLoad/host scratch in the dump.
        from cd32_runtime import BASE,SIZES
        x,y=[(p/(name+'-fast.bin')).read_bytes() for p in (a,b)]
        if len(x)!=0x800000 or len(y)!=0x800000:raise ValueError('truncated RAM')
        for base,size in zip(ma['hunks'],SIZES):
            offset=base-BASE
            if x[offset:offset+size]!=y[offset:offset+size]:raise ValueError('game state differs: '+name)
    return {'milestones':len(ma['milestones']),'events':len(ea),'identical':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--repeat',type=Path);p.add_argument('--counter',type=Path)
    a=p.parse_args();meta=json.loads((a.run/'result.json').read_text());events=run_events(a.run,meta)
    result={'trace_validation':validate_trace(a.run/'origin-animation.bin',events,meta['hunks'][0])}
    result['flight_trace_validation']=validate_trace(a.run/'credits-00.bin',events,meta['hunks'][0])
    if a.counter:
        counter=json.loads((a.counter/'result.json').read_text())
        full=result['trace_validation']
        for key in ('slave_sha256','emulator_sha256','cpu_multiplier','cpu_frequency'):
            if counter[key]!=meta[key]:raise ValueError('counter build mismatch: '+key)
        if not counter['complete'] or counter['fields']!=full['fields'] or counter['counts']!=full['counts']['0x3378e']:
            raise ValueError('independent SWAP_ONLY/full trace disagreement')
        vbl=[e for e in events if e[0]==meta['hunks'][0]+0x34162 and full['field_base']<=e[1]<=full['field_base']+full['fields']]
        if counter['vbls']!=[[e[1]-full['field_base'],e[24]] for e in vbl]:
            raise ValueError('independent counter used a different emulated interval')
        result['independent_swap_only']=True
    if a.repeat: result['repeat']=compare(a.run,a.repeat)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
