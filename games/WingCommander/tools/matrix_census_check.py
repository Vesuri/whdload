#!/usr/bin/env python3
"""Check the host change census against independently read GDB chunky snapshots."""
import argparse
import json
from pathlib import Path


def check(run):
    meta = json.loads((run/'result.json').read_text())
    samples = meta.get('chunky_oracle', [])
    if not meta['complete'] or len(samples) != 6:
        raise ValueError('six completed source snapshots required')
    census = []
    for line in (run/'matrix-events.txt').read_text().splitlines():
        fields = line.split()
        if fields[0] == 'C' and int(fields[1]) == 4:
            census.append(tuple(int(v) for v in fields[4:8]))
    if len(census) < len(samples):
        raise ValueError('census does not cover source snapshots')
    previous = None
    checked = []
    for index, sample in enumerate(samples):
        if sample['scene'] != 4 or sample['index'] != index:
            raise ValueError('unexpected source snapshot order')
        if (sample['width'], sample['height']) != (320, 128):
            raise ValueError('oracle geometry is outside the checked scope')
        data = (run/sample['file']).read_bytes()
        if len(data) != sample['width']*sample['height']:
            raise ValueError('truncated source snapshot')
        compared = previous is not None and len(previous) == len(data)
        changed = sum(a != b for a, b in zip(data, previous)) if compared else 0
        blocks = sum(data[p:p+32] != previous[p:p+32] for p in range(0, len(data), 32)) if compared else 0
        expected = (len(data), int(compared), changed, blocks)
        if census[index] != expected:
            raise ValueError(f'chunky census mismatch at sample {index}')
        checked.append(dict(index=index, bytes=len(data), compared=compared,
                            changed_bytes=changed, changed_blocks=blocks))
        previous = data
    return dict(chunky_oracle_pass=True, scene='origin-animation', samples=checked,
                scope='First six 320x128 c2p entries; first is unpaired. No 166/200-line or whole-run validation claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.run), indent=2))


if __name__ == '__main__':
    main()
