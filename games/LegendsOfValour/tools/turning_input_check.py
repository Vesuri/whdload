#!/usr/bin/env python3
"""Check one-degree input from completed-tick guest observations."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--sweep', choices=('forward', 'reverse'))
p.add_argument('--hold', action='store_true')
a = p.parse_args()
root = a.capture/'ticks'
meta = json.loads((root/'metadata.json').read_text())
assert meta.get('complete') and meta.get('sample_unit') == 'completed tick'
samples = json.loads((root/'samples.json').read_text())
assert len(samples) > 2
for previous, current in zip(samples, samples[1:]):
    assert current['simulation']['started_ticks'] == previous['simulation']['started_ticks']+1
for s in samples:
    heading = s['player']['heading']
    assert 0 <= heading < 360 and heading == s['player']['quantized_heading']

if a.sweep:
    direction = 1 if a.sweep == 'forward' else -1
    count = wraps = 0
    for previous, current in zip(samples, samples[1:]):
        old, new = previous['player']['heading'], current['player']['heading']
        delta = (new-old)*direction % 360
        assert delta in (0,1), (old,new,'non-unit movement')
        mouse = (current['input_sample']['mouse_x']-previous['input_sample']['mouse_x'])*direction % 65536
        assert mouse == delta, (old,new,'input/heading mismatch',mouse)
        count += delta
        wraps += int(delta == 1 and (new-old)*direction < 0)
    assert count == 360 and wraps == 1, (count,wraps)
    assert len({s['player']['heading'] for s in samples}) == 360
    print(f'360 exact one-degree {a.sweep} steps; all headings and one wrap verified')
else:
    starts = [i for i in range(1,len(samples))
              if samples[i]['input_sample']['buttons'] == 1
              and samples[i-1]['input_sample']['buttons'] == 0]
    assert len(starts) == 1, starts
    i = starts[0]
    before = samples[i-1]['player']['heading']
    assert samples[i]['player']['heading'] == (before+5)%360
    if a.hold:
        end = next(j for j in range(i+1,len(samples)) if samples[j]['input_sample']['buttons'] == 0)
        assert end-i == 20, (i,end)
        changes = [(samples[j]['player']['heading']-samples[j-1]['player']['heading'])%360 for j in range(i,end)]
        assert changes == [5]*20, changes
        assert all(s['player']['heading'] == samples[end-1]['player']['heading'] for s in samples[end:])
        print('Held right press: native 5 degrees/tick from the first tick; release stops')
    else:
        end = next(j for j in range(i+1,len(samples)) if samples[j]['input_sample']['buttons'] == 0)
        changes = [(samples[j]['player']['heading']-samples[j-1]['player']['heading'])%360 for j in range(i,end)]
        assert changes == [5]*(end-i), changes
        assert all(s['player']['heading'] == samples[end-1]['player']['heading'] for s in samples[end:])
    assert len(samples)-i >= 10 and samples[-1]['input_sample']['buttons'] == 0
    if not a.hold:
        print('Short right press: native 5 degrees/tick; no movement after release')
