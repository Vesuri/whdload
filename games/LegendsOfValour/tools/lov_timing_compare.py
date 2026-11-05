#!/usr/bin/env python3
"""Compare decoded persistent-world samples from a pair of equal-time captures."""
import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('normal', type=Path)
    p.add_argument('delayed', type=Path)
    p.add_argument('--ticks', action='store_true', help='compare completed-tick samples, retaining wall-clock differences in the report')
    a = p.parse_args()
    folder = 'ticks' if a.ticks else 'state'
    for capture in (a.normal, a.delayed):
        metadata=capture / folder / 'metadata.json'
        if metadata.exists() and json.loads(metadata.read_text()).get('complete') is False:
            p.error(f'{capture}: observation stopped early; partial samples are not a complete comparison')
    first = json.loads((a.normal / folder / 'samples.json').read_text())
    second = json.loads((a.delayed / folder / 'samples.json').read_text())
    def elapsed(samples):
        if a.ticks:
            return [s['simulation']['started_ticks'] for s in samples]
        return [(s['field'] - samples[0]['field']) & 0xffffffff for s in samples]
    if not first or not second:
        p.error('both captures need nonempty sample lists')
    for samples in (first, second):
        if any([actor['index'] for actor in sample['actors']] != list(range(56)) for sample in samples):
            p.error('each sample must contain all 56 actor records in order')
    if elapsed(first) != elapsed(second):
        p.error('samples cover different tick numbers' if a.ticks else 'samples cover different elapsed-field intervals')
    # Absolute boot field counts may differ; every interpreted world field must match.
    def world(sample):
        return {k: v for k, v in sample.items() if k not in ('field', 'simulation')}
    first_difference = {}
    for x, y, field in zip(first, second, elapsed(first)):
        for category in sorted(world(x).keys() | world(y).keys()):
            if x.get(category) != y.get(category):
                first_difference.setdefault(category, field)
    report = dict(comparison_unit='completed tick' if a.ticks else 'elapsed VBL field',
                  first_difference=first_difference, initial_world_equal=world(first[0]) == world(second[0]),
                  elapsed_counter_fields=[(s[-1]['field']-s[0]['field']) & 0xffffffff for s in (first,second)], samples=len(first),
                  sample_interval=[elapsed(first)[0],elapsed(first)[-1]],
                  different_final_actors=[x['index'] for x, y in
                      zip(first[-1]['actors'], second[-1]['actors']) if x != y],
                  final_player_equal=first[-1]['player'] == second[-1]['player'],
                  final_rng=[first[-1]['rng'], second[-1]['rng']],
                  final_animation=[first[-1]['animation'], second[-1]['animation']],
                  final_periodic_count=[first[-1]['periodic_count'], second[-1]['periodic_count']])
    print(json.dumps(report, indent=2))
if __name__ == '__main__':
    main()
