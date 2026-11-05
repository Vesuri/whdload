#!/usr/bin/env python3
"""Price contiguous native tick logic between render return and next render.

Discard intervals crossing capture gaps. Include interrupts/OS cycles occurring
inside each interval: these are elapsed CPU-clock costs, not task self costs.
The retained A traces predate B and the new scheduler; this is a feasibility
baseline, not proof of the finished scheduler's sustained performance.
"""
import json, statistics
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
root=Path(__file__).resolve().parents[1]
report={}
for scene in ('takeoff','hover','combat'):
    p=root/'tmp/a-final/matrix'/scene/'a500-fast'
    h=json.loads((p/'layout.json').read_text())['hunks'][0]
    samples=[]
    for path in sorted(p.glob('chunk_*.bin')):
        trace=barto.load(path)
        cycles=None
        for field in trace.fields:
            for pc,cost,regs in trace.instructions(field):
                if pc==h+0x5836:
                    assert cycles is None
                    cycles=0
                if pc==h+0x5830 and cycles is not None:
                    samples.append(cycles)
                    cycles=None
                if cycles is not None:
                    cycles+=cost
    assert samples, scene
    report[scene]=dict(samples=len(samples),cycles=samples,
        mean_cycles=statistics.mean(samples),max_cycles=max(samples),
        mean_fields=statistics.mean(samples)/142101,
        max_fields=max(samples)/142101,
        utilization_at_18_fields=statistics.mean(samples)/(18*142101))
out=root/'tmp/c/tick-cost.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
