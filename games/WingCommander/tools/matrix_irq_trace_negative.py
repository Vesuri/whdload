#!/usr/bin/env python3
"""Reject damaged trace clocks and callback durations in retained tmp fixtures."""
import argparse
import json
from pathlib import Path
from cd32_runtime import ROOT
from matrix_irq_trace_check import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = args.run.resolve()
    output = args.output.resolve()
    if (ROOT/'tmp').resolve() not in output.parents or output.exists():
        raise ValueError('fresh tmp output required')
    validated = check(source)
    serial = validated['rows'][0]['serial']
    lines = (source/'irq-events.txt').read_text().splitlines()
    output.mkdir()
    results = []
    for name in ('short-duration', 'long-duration', 'field-clock'):
        dest = output/name
        dest.mkdir()
        for file in ('result.json', 'matrix-events.txt', 'fast.bin', 'irq-trace.bin'):
            (dest/file).symlink_to(source/file)
        changed = []
        mutations = 0
        for line in lines:
            p = line.split()
            if name == 'field-clock' and p[:3] == ['F', '0', '0']:
                p[3] = str(int(p[3])-128)
                mutations += 1
            elif name != 'field-clock' and p[:2] == ['R', str(serial)]:
                p[2] = str(int(p[2])+(-1 if name == 'short-duration' else 1))
                mutations += 1
            changed.append(' '.join(p))
        if mutations != 1:
            raise ValueError('negative fixture did not change exactly one record')
        (dest/'irq-events.txt').write_text('\n'.join(changed)+'\n')
        try:
            check(dest)
        except ValueError as error:
            results.append(dict(fixture=name, rejected=True, reason=str(error)))
        else:
            raise ValueError('corrupted trace accepted: '+name)
    (output/'result.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
