#!/usr/bin/env python3
"""Reduce an A7/A8 window to complete-call timings and chip slots.
Usage: matrix_report.py CAPTURE
040/060 figures describe the emulator model, not accelerator hardware timings.
"""
import collections
import json
from pathlib import Path
import sys
import struct
from race_profile import StackReduction, image


def stats(values):
    if not values:
        return None
    values = sorted(values)
    return dict(count=len(values), mean=sum(values)/len(values),
                p50=values[len(values)//2], p95=values[min(len(values)-1, int(len(values)*.95))],
                maximum=values[-1])


def report(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    red = StackReduction.load(root/'profile.pkl.gz')
    fields = len(red.fields)
    cycles = sum(f['cycles'] for f in red.fields)
    scale = fields*20/cycles
    pending, calls = {}, collections.defaultdict(list)
    frame_events = []
    for name, pos, wait in red.events:
        if name == 'frame':
            frame_events.append((pos, wait))
        elif name.endswith('_end'):
            kind = name[:-4]
            if kind in pending:
                calls[kind].append((pos-pending.pop(kind))*scale)
        else:
            if name in pending:
                raise ValueError(f'nested/unclosed {name} call')
            pending[name] = pos
    spans = [(b[0]-a[0])*scale for a,b in zip(frame_events, frame_events[1:])]
    work = [((b[0]-a[0])-(b[1]-a[1]))*scale for a,b in zip(frame_events, frame_events[1:])]
    dma = collections.Counter()
    for f in red.fields:
        dma.update(f['dma'])
    def extra(name):
        p = root/name
        return p.read_bytes() if p.exists() else b''
    memory = image((root/'chip.bin').read_bytes(), extra('fast.bin'), extra('slow.bin'))
    h0 = meta['hunk_bases'][0]
    def fixed_ms(offset):
        whole, fraction = struct.unpack_from('>IH', memory, h0+offset)
        return whole + fraction/65536
    fps = 1000*len(spans)/sum(spans) if spans else None
    unavailable = []
    if not red.counts:
        unavailable.append('trace contains no CPU instruction records')
    for name, values in (('frame', spans), ('drawing', calls['draw']), ('tick', calls['tick'])):
        if not values:
            unavailable.append(f'no complete {name} samples')
    return dict(status='UNAVAILABLE' if unavailable else 'MEASURED', unavailable=unavailable,
                instruction_records=sum(red.counts.values()),
                phase=meta['phase'], setup=meta['setup'], hunk_bases=meta['hunk_bases'],
                fields=fields, cycles_per_field=cycles/fields,
                fps=fps, game_clock_step_ms=fixed_ms(0x3a7de),
                native_step_ms=fixed_ms(0x3a7e4),
                game_clock_ratio=fps*fixed_ms(0x3a7de)/1000 if fps else None,
                frame_ms=stats(spans), work_ms=stats(work),
                drawing_ms=stats(calls['draw']), tick_ms=stats(calls['tick']),
                chip_slots_per_field={str(k): v/fields for k,v in sorted(dma.items())})


if __name__ == '__main__':
    result = report(sys.argv[1])
    (Path(sys.argv[1])/'metrics.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
