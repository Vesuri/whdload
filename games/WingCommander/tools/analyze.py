#!/usr/bin/env python3
"""Explicit-variant analysis front door; no emulator runs or guest writes."""
import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys
from variants import get


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=('cd32', 'ocs'), required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('definitions', help='print verified English definitions, no game bytes')
    layout = sub.add_parser('layout', help='discover a live layout in a Fast RAM dump')
    layout.add_argument('memory', type=Path)
    static = sub.add_parser('static', help='reproduce the pinned static inventory in tmp/')
    static.add_argument('--output', required=True)
    args = parser.parse_args()
    variant = get(args.variant)
    if args.action == 'definitions':
        print(json.dumps({key.lower(): value for key, value in vars(variant).items()
                          if key.isupper()}, indent=2))
    elif args.action == 'layout':
        runtime = importlib.import_module(args.variant + '_runtime')
        print(json.dumps(dict(variant=args.variant, **runtime.locate(args.memory.read_bytes())), indent=2))
    else:
        subprocess.run([sys.executable, str(Path(__file__).with_name(args.variant + '_static.py')),
                        '--output', args.output], check=True)


if __name__ == '__main__':
    main()
