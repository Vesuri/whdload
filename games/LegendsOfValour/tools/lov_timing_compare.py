#!/usr/bin/env python3
"""Compare decoded persistent-world samples from a pair of equal-time captures."""
import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('normal', type=Path)
    p.add_argument('delayed', type=Path)
    a = p.parse_args()
    first = json.loads((a.normal / 'state/samples.json').read_text())
    second = json.loads((a.delayed / 'state/samples.json').read_text())
    def elapsed(samples):
        return [(s['field'] - samples[0]['field']) & 0xffffffff for s in samples]
    if not first or not second:
        p.error('both captures need nonempty sample lists')
    for samples in (first, second):
        if any([actor['index'] for actor in sample['actors']] != list(range(56)) for sample in samples):
            p.error('each sample must contain all 56 actor records in order')
    if elapsed(first) != elapsed(second):
        p.error('samples cover different elapsed-field intervals')
    # Absolute boot field counts may differ; every interpreted world field must match.
    def world(sample):
        return {k: v for k, v in sample.items() if k != 'field'}
    first_difference = {}
    for x, y, field in zip(first, second, elapsed(first)):
        for category in sorted(world(x).keys() | world(y).keys()):
            if x.get(category) != y.get(category):
                first_difference.setdefault(category, field)
    report = dict(first_different_elapsed_field=first_difference, initial_world_equal=world(first[0]) == world(second[0]),
                  elapsed_counter_fields=elapsed(first)[-1], samples=len(first),
                  different_final_actors=[x['index'] for x, y in
                      zip(first[-1]['actors'], second[-1]['actors']) if x != y],
                  final_player_equal=first[-1]['player'] == second[-1]['player'],
                  final_rng=[first[-1]['rng'], second[-1]['rng']],
                  final_animation=[first[-1]['animation'], second[-1]['animation']],
                  final_periodic_count=[first[-1]['periodic_count'], second[-1]['periodic_count']])
    print(json.dumps(report, indent=2))
if __name__ == '__main__':
    main()
