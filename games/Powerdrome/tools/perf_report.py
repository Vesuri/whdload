#!/usr/bin/env python3
"""Measure completed Practice scenes and presentation intervals in one trace.
CPU costs are comparable only within the same emulator CPU/timing configuration.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import struct
import barto
from perf_status import status


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    args = p.parse_args()
    root = args.capture
    t = barto.load(root / 'trace.bin')
    game = int((root / 'game-base.txt').read_text(), 0)
    chip = (root / 'chip.bin').read_bytes()
    other = (root / 'code.bin').read_bytes()
    component_ranges = {}
    if chip[game + 0x10df2:game + 0x10df4] == b'\x4e\xf9':
        wrapper = struct.unpack_from('>I', chip, game + 0x10df4)[0]
        # Version 03 and later carry relative seed/copy interval labels.
        sig = other.rfind(b'PDPERF03')
        if sig >= 0:
            bounds = struct.unpack_from('>4h', other, sig + 50)
            for name, lo, hi in zip(('seed', 'copy'), bounds[::2], bounds[1::2]):
                assert 0 <= lo < hi < 4096
                component_ranges[name] = (wrapper + lo, wrapper + hi)
    counts = Counter()
    scenes = []
    presentations = []
    deltas = []
    current = None
    cycles = 0
    native = False
    component = None
    armed = False
    post_render = False
    driving_present = False
    for f in t.fields:
        for pc, cost, regs in t.instructions(f):
            off = pc - game if pc is not None else -1
            if off == 0xcee8:
                armed = True
            if off == 0x10df2 and armed:
                armed = False
                assert current is None, 'Nested scene renderer'
                current = Counter()
                current['start_field'] = f.index
                counts['renderer_entries'] += 1
            if off == 0x10df8 and current is not None:
                native = True
            if off == 0xceec and current is not None:
                current['end_field'] = f.index
                scenes.append(dict(current))
                post_render = True
                current = None
                native = False
            if off == 0xbc7c:
                driving_present = True
                presentations.append({'field': f.index, 'cycles': cycles})
            if off == 0xccf2:
                counts['movement_updates'] += 1
            if off == 0xd8ea and post_render:
                post_render = False
                counts['post_render_updates'] += 1
            if off == 0x5684:
                counts['vbl_callbacks'] += 1
            if off == 0x7fa4 and driving_present:
                driving_present = False
                deltas.append(regs[6] & 65535)
            for name, (lo, hi) in component_ranges.items():
                if pc == lo:
                    component = name
                elif pc == hi:
                    component = None
            if current is not None:
                current['total_cycles'] += cost
                category = 'native_scene' if native else 'wrapper_and_sync'
                if component is not None:
                    category = component
                current[category] += cost
            if off == 0x117da:
                native = False
            cycles += cost
    summary = {}
    for key in ('total_cycles', 'native_scene', 'seed', 'copy', 'wrapper_and_sync'):
        values = sorted(s.get(key, 0) for s in scenes)
        if values:
            summary[key] = {'mean': statistics.mean(values), 'median': statistics.median(values),
                            'p95': values[min(len(values)-1, int(len(values)*.95))],
                            'min': values[0], 'max': values[-1]}
    fps = None
    if len(presentations) > 1:
        fields = presentations[-1]['field'] - presentations[0]['field']
        if fields:
            fps = {'completed_intervals': len(presentations)-1, 'fields': fields,
                   'nominal_pal_fps': 50*(len(presentations)-1)/fields}
    result = {'fields': len(t.fields), 'counts': counts, 'completed_scenes': len(scenes),
              'incomplete_scene_excluded': current is not None, 'scene_costs': summary,
              'presentation_rate': fps, 'presentations': presentations,
              'elapsed_time_deltas': deltas, 'scenes': scenes}
    try:
        result['diagnostics'] = status(root/'final-code.bin')
    except AssertionError:
        pass
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
