#!/usr/bin/env python3
"""Retain negative beam/stack/order calibration fixtures under tmp."""
import argparse
import json
from pathlib import Path
from cd32_runtime import ROOT
from matrix_irq_beam_check import check, position


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    source=args.run.resolve();output=args.output.resolve()
    if (ROOT/'tmp').resolve() not in output.parents or output.exists():
        raise ValueError('fresh tmp output required')
    check(source)
    # PAL horizontal wrap and the last line of a long field.
    assert position(0x80000001)==(227,313*227)
    assert position(0x80000000)==(226,313*227)
    assert position(0x80000102)==(228,313*227)
    assert position(0x80013801)==(0,313*227)
    output.mkdir();results=[]
    for name in ('beam-clock','return-stack','callback-order'):
        dest=output/name;dest.mkdir()
        for file in ('result.json','matrix-events.txt','irq-events.txt'):
            (dest/file).symlink_to(source/file)
        samples=json.loads((source/'irq-beam.json').read_text())
        if name=='beam-clock':
            beam=samples[0]['end']['beam']
            if not 1<(beam&255)<223:raise ValueError('fixture needs room before line wrap')
            samples[0]['end']['beam']=beam+4
        elif name=='return-stack':samples[0]['end']['sp']+=4
        else:samples[0]['kind']=1
        (dest/'irq-beam.json').write_text(json.dumps(samples,indent=2)+'\n')
        try:check(dest)
        except ValueError as error:results.append(dict(fixture=name,rejected=True,reason=str(error)))
        else:raise ValueError('corrupt beam fixture accepted: '+name)
    (output/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
