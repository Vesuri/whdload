#!/usr/bin/env python3
"""Repeatable normal-build Barto/flat-aprof capture; records actual race-field bounds."""
import argparse,json,os
from harness_a import *
from amigaxdev.aprof import parse_profile
from amigaxdev.callprofile import Reduction

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--kind',choices=['barto','aprof'],default='barto');ap.add_argument('--fields',type=int,default=500)
    args=ap.parse_args()
    slave=Path(os.environ.get('SLAVE',ROOT/'tmp/build/RoadRash.slave')).resolve();os.environ['SLAVE']=str(slave)
    out=Path(args.out)
    if (out/'profile.json').exists():raise RuntimeError('choose a fresh output directory')
    s=Session(out)
    try:
        initial=route(s);s.input('JOY2_UP',1)
        if os.environ.get('RR_LISTING'):
            listing=Path(os.environ['RR_LISTING']).read_text(encoding='latin1')
            symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)$',listing,re.M)}
            slave_base=rd(s,0x87480)-symbols['step_main']
            (s.out/'placement.json').write_text(json.dumps(dict(base=slave_base,symbols=symbols),indent=2)+'\n')
        if args.kind=='barto':
            reduction=Reduction();chunks=[];remaining=args.fields
            while remaining:
                elapsed=min(100,remaining)
                if elapsed<2:raise ValueError('profile window must not leave a single-field tail')
                p=s.out/f'trace-{len(chunks):02d}.bin';start=field(s)
                s.cmd(f'monitor profile {elapsed-1} "" "{p}"',timeout=240)
                trace=reduction.feed(str(p))
                chunks.append(dict(start=start,end=field(s),trace_fields=len(trace.fields),bytes=p.stat().st_size))
                print('Barto chunk',chunks[-1],flush=True);remaining-=elapsed
            reduction.save(str(s.out/'profile.pkl.gz'))
            (s.out/'last-field.png').write_bytes(trace.fields[-1].shot)
            details=dict(chunks=chunks,note='Each chunk skips the initial partial field; no emulated work is inserted between captures. Counts cover recorded fields, not the entire elapsed window.')
        else:
            s.cmd('monitor aprof start')
            advance(s,100+args.fields)
            p=s.out/'aprof.txt';s.cmd(f'monitor aprof stop {p}')
            header,pcs,nodes=parse_profile(p.read_text())
            details=dict(header=header,top_instructions=sorted((dict(pc=hex(pc),units=v[0],executions=v[1],chip_units=v[2],chip_accesses=v[3]) for pc,v in pcs.items()),key=lambda x:x['executions'],reverse=True)[:50],
                         top_chip=sorted((dict(pc=hex(pc),units=v[0],executions=v[1],chip_units=v[2],chip_accesses=v[3]) for pc,v in pcs.items()),key=lambda x:x['chip_units'],reverse=True)[:50],
                         interpretation='Flat PCs only; 040/060 instruction counts and Chip time, not hardware CPU cycle costs. Inclusive call costs require validated return pairing.')
        end=snapshot(s)
        if end['field']!=100+args.fields:raise RuntimeError(f'profile ended at unexpected field {end["field"]}')
        result=dict(kind=args.kind,provenance=provenance(slave,s),initial=initial,end=end,details=details)
        (s.out/'profile.json').write_text(json.dumps(result,indent=2)+'\n');print('profile complete',args.kind,initial['field'],end['field'],flush=True)
    finally:s.quit()

if __name__=='__main__':main()
