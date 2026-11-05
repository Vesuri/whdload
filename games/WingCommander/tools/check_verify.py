#!/usr/bin/env python3
"""Check VERIFY marker gating and exact game-state/picture equivalence."""
import argparse
import json
from pathlib import Path
from compare_boots import compare
from cd32_runtime import BASE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('reference', 'off', 'on'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    for path, expected in ((args.reference, 0), (args.off, 0), (args.on, 1)):
        for prefix in ('', 'name-'):
            metadata = json.loads((path/(prefix+'result.json')).read_text())
            memory = (path/(prefix+'fast.bin')).read_bytes()
            offset = metadata['slave'] - BASE + 0x1e34
            if len(memory) != 0x800000 or not 0 <= offset <= len(memory)-4:
                raise ValueError('invalid retained fast-RAM dump')
            marker = int.from_bytes(memory[offset:offset+4], 'big')
            if marker != expected:
                raise ValueError(f'{path}/{prefix}marker: {marker}, expected {expected}')
    for path in (args.off, args.on):
        for prefix in ('', 'name-'):
            if not compare(args.reference, path, prefix)['pass']:
                raise SystemExit(1)
    print('VERIFY off/on markers and both endpoints: PASS')


if __name__ == '__main__':
    main()
