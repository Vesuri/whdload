#!/usr/bin/env python3
"""Check the sprite-frame phase consumed at h5:02264 in completed-tick captures."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    root = args.capture / 'ticks'
    metadata = json.loads((root / 'metadata.json').read_text())
    if not metadata.get('complete') or metadata.get('sample_unit') != 'completed tick':
        parser.error('requires a complete completed-tick capture')
    samples = json.loads((root / 'samples.json').read_text())
    changes = 0
    for before, after in zip(samples, samples[1:]):
        tick = after['simulation']['started_ticks']
        if tick != before['simulation']['started_ticks'] + 1:
            parser.error('requires consecutive simulation ticks')
        a, b = before['animation'], after['animation']
        pacing = a['pacing']
        if pacing < 1 or b['pacing'] != pacing:
            parser.error(f'animation pacing changes or is invalid at tick {tick}')
        advance = a['count'] + 1 >= pacing
        expected_count = 0 if advance else a['count'] + 1
        expected_phase = (a['phase'] + int(advance)) % 4
        if b['count'] != expected_count or b['phase'] != expected_phase:
            parser.error(f'tick {tick}: expected count/phase {expected_count}/{expected_phase}, '
                         f'got {b["count"]}/{b["phase"]}')
        changes += int(advance)
    if len(samples) < 2 or changes < 2:
        parser.error('capture must cover at least two sprite-phase advances')
    print(f'{len(samples)-1} ticks: {changes} sprite-phase advances; delay honored')


if __name__ == '__main__':
    main()
