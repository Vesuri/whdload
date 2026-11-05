#!/usr/bin/env python3
"""Check DMA summaries against field geometry and the independent Barto menu trace."""
import argparse
import collections
import json
import struct
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from matrix_scene_report import report as scene_report

NAMES = ('unclaimed','refresh','cpu','copper','audio','blitter','bitplanes','sprites','disk','conflict','unknown')


def check(run):
    meta=json.loads((run/'result.json').read_text())
    if not meta.get('dma'):raise ValueError('DMA-enabled capture required')
    scenes=scene_report(run)['scenes']
    fields=[]; field_ids=set(); assigned=collections.defaultdict(lambda:[0]*len(NAMES))
    scene_counts=collections.defaultdict(lambda:[0]*len(NAMES))
    for line in (run/'dma-events.txt').read_text().splitlines():
        p=line.split()
        if p[0]=='F':
            if len(p)!=17:raise ValueError('malformed field summary')
            field,start,end,height,slots=map(int,p[1:6]); counts=list(map(int,p[6:]))
            if any(x<0 for x in counts) or sum(counts)!=slots or end-start!=slots*512:
                raise ValueError('DMA field accounting mismatch')
            if height not in (312,313) or not height*226<=slots<=height*228:
                raise ValueError('unsupported field geometry')
            if fields and (field!=fields[-1]['field']+1 or start!=fields[-1]['end']):
                raise ValueError('missing/discontinuous DMA field')
            if field in field_ids:raise ValueError('duplicate field')
            field_ids.add(field)
            fields.append(dict(field=field,start=start,end=end,height=height,slots=slots,counts=counts))
        elif p[0]=='D':
            if len(p)!=14:raise ValueError('malformed scene assignment')
            scene,field=int(p[1]),int(p[2]);counts=list(map(int,p[3:]))
            if not 0<=scene<34 or not fields or field!=fields[-1]['field'] or any(x<0 for x in counts):
                raise ValueError('invalid scene assignment')
            for i,value in enumerate(counts):
                assigned[field][i]+=value;scene_counts[scene][i]+=value
        else:raise ValueError('unknown DMA record')
    if not fields:raise ValueError('empty DMA capture')
    for f in fields:
        if any(a>b for a,b in zip(assigned[f['field']],f['counts'])):
            raise ValueError('scene assignment exceeds field total')
    trace=barto.load(str(run/'menu.bin'))
    if len(trace.fields)!=1:raise ValueError('one independent menu field expected')
    reference=[0]*len(NAMES)
    dma=trace.fields[0].dma
    if len(dma)!=58*227*313:raise ValueError('unexpected Barto DMA layout')
    for offset in range(0,len(dma),58):
        kind=struct.unpack_from('<h',dma,offset+29)[0]
        reference[kind if 0<=kind<10 else 10]+=1
    if fields[-1]['counts']!=reference or fields[-1]['slots']!=227*313:
        raise ValueError('independent menu DMA histogram disagrees')
    output=[]
    for i,scene in enumerate(scenes):
        counts=scene_counts[i];slots=sum(counts);delta=slots*512-scene['units']
        # First field can begin after reset. Every later scene must be covered
        # to within one slot when assigning by the slot's left boundary.
        if i>0 and abs(delta)>512:raise ValueError('incomplete scene DMA coverage: '+scene['scene'])
        output.append(dict(scene=scene['scene'],slots=slots,coverage_delta_units=delta,
                           counts=dict(zip(NAMES,counts)),
                           shares={name:count/slots if slots else None for name,count in zip(NAMES,counts)}))
    return dict(field_accounting_pass=True,independent_menu_histogram_pass=True,
                fields=len(fields),scenes=output,validated_baseline=False,
                limitations=['Scene boundaries are assigned at 512-unit slot resolution.',
                             'Unclaimed bus slots are not CPU idle time.',
                             'DMA recording neutrality must pass separately.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
    args=parser.parse_args();print(json.dumps(check(args.run),indent=2))
