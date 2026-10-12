#!/usr/bin/env python3
"""Reject structurally damaged phase 4 diagnostics; this does not validate timing."""
import argparse
import json
from pathlib import Path
from matrix_report import report

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = args.run.resolve()
    output = args.output.resolve()
    if (ROOT/'tmp').resolve() not in output.parents or output.exists():
        raise ValueError('new output below tmp/ required')
    report(source)  # The undamaged fixture must parse first.
    output.mkdir(parents=True)
    results = {}
    for name in ('missing-cut', 'wrong-cache', 'bad-change', 'wrong-clock'):
        target = output/name
        target.mkdir()
        (target/'result.json').symlink_to(source/'result.json')
        for profile in source.glob('scene-*.aprof'):
            if name == 'wrong-clock' and profile.name == 'scene-04.aprof':
                text = profile.read_text()
                assert 'cycleunit 128' in text
                (target/profile.name).write_text(text.replace('cycleunit 128', 'cycleunit 115'))
            else:
                (target/profile.name).symlink_to(profile)
        lines = (source/'matrix-events.txt').read_text().splitlines()
        changed = False
        for index, line in enumerate(lines):
            fields = line.split()
            if name == 'missing-cut' and line.startswith('B 5 '):
                del lines[index]
            elif name == 'wrong-cache' and fields[0] == 'P':
                fields[4] = 'ffffffff'
                lines[index] = ' '.join(fields)
            elif name == 'bad-change' and fields[0] == 'C' and fields[5] == '1':
                fields[6] = str(int(fields[4])+1)
                lines[index] = ' '.join(fields)
            else:
                continue
            changed = True
            break
        assert changed or name == 'wrong-clock'
        (target/'matrix-events.txt').write_text('\n'.join(lines)+'\n')
        try:
            report(target)
        except ValueError as error:
            results[name] = str(error)
        else:
            raise AssertionError('damaged fixture accepted: '+name)
    (output/'result.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
