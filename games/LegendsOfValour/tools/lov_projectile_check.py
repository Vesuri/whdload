#!/usr/bin/env python3
"""Verify native type-130 projectile motion and collision in completed-tick captures."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--thrown', action='store_true', help='check the native type-55 throw arc and landing')
p.add_argument('--compare', type=Path)
a = p.parse_args()

def check(root):
    meta = json.loads((root/'ticks/metadata.json').read_text())
    assert meta.get('complete') and meta.get('sample_unit') == 'completed tick'
    samples = json.loads((root/'ticks/samples.json').read_text())
    initial = samples[0]['projectiles']
    spawned = [(n, item['index']) for n, sample in enumerate(samples[1:], 1)
               for item in sample['projectiles']
               if item['type'] == (55 if a.thrown else 130) and initial[item['index']]['type'] == 0]
    assert spawned, 'fixture did not launch a projectile'
    slots = {index for _, index in spawned}
    assert len(slots) == 1, 'expected one native launch'
    index = slots.pop()
    active = [n for n, slot in spawned if slot == index]
    assert len(active) >= 2 and active == list(range(active[0], active[-1]+1))
    if not a.thrown:
        assert active[-1]+1 < len(samples), 'collision/despawn not observed'
    for n in active[1:]:
        prev, cur = [samples[k]['projectiles'][index] for k in (n-1,n)]
        # Collision probing may shorten the final approach to a wall.
        for axis, speed in (('x','velocity_x'),('y','velocity_y')):
            delta = cur[axis]-prev[axis]
            assert abs(delta) <= abs(prev[speed])
            assert delta * prev[speed] >= 0
    assert any(samples[n]['projectiles'][index]['x'] != samples[n-1]['projectiles'][index]['x'] or
               samples[n]['projectiles'][index]['y'] != samples[n-1]['projectiles'][index]['y'] for n in active[1:]), 'projectile never moved'
    if a.thrown:
        heights = [samples[n]['projectiles'][index]['height'] for n in active]
        assert max(heights) > heights[0] > 0, 'no upward arc'
        landing = next((n for n in active if samples[n]['projectiles'][index]['height'] == 0), None)
        assert landing is not None and landing > active[0], 'no landing'
        resting = samples[landing]['projectiles'][index]
        assert resting['velocity_x'] == resting['velocity_y'] == resting['vertical'] == 0
        assert all(sample['projectiles'][index] == resting for sample in samples[landing:]), 'landed item keeps moving'
        print(root.name, f'slot {index}: apex {max(heights)}, landed at sample {landing}')
    else:
        for n in active:
            assert samples[n]['projectiles'][index]['height'] == 24
        prev = samples[active[-1]]['projectiles'][index]
        collision = samples[active[-1]+1]['projectiles'][index]
        assert collision['type'] == 0 and collision['height'] == 0
        assert (collision['velocity_x'],collision['velocity_y']) != (prev['velocity_x'],prev['velocity_y']), 'no collision response'
        print(root.name, f'slot {index}: {len(active)} active samples, collision at sample {active[-1]+1}')
    assert all(s['simulation']['input_recoveries'] == 0 for s in samples)
    return samples

first = check(a.capture)
if a.compare:
    second = check(a.compare)
    assert len(first) == len(second)
    for x,y in zip(first,second):
        assert x['simulation']['started_ticks'] == y['simulation']['started_ticks']
        assert x['logical_clock'] == y['logical_clock']
        # Live game time and rendering debt differ; logical world state must not.
        assert {k:v for k,v in x.items() if k not in ('field','game_clock','simulation')} == {
               k:v for k,v in y.items() if k not in ('field','game_clock','simulation')}, 'world diverged under drawing delay'
    print('All logical world and projectile snapshots match under drawing delay')
