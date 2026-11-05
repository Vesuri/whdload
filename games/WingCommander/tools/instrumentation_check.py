#!/usr/bin/env python3
"""Explicit variant entry point for native instrumentation acceptance."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from variants import get

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant', required=True, choices=('cd32', 'ocs'))
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--control', type=Path, help='required OCS observer-off capture')
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args(); v = get(a.variant)
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        p.error('new tmp output required')
    if v.NAME == 'ocs' and not a.control:
        p.error('OCS requires its matched observer-off control')
    if v.NAME == 'cd32' and a.control:
        p.error('CD32 retains its existing recorder/observer gate; no OCS control semantics')
    a.output.mkdir(parents=True)
    if v.NAME == 'ocs':
        from ocs_instrumentation import check
        result = check(a.run, a.control, a.output)
        (a.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    else:
        subprocess.run([sys.executable, str(ROOT/'tools/frame_check.py'), str(a.run),
                        '--output', str(a.output/'report.json')], check=True)
    print('PASS: '+v.NAME+' instrumentation gate')


if __name__ == '__main__':
    main()
