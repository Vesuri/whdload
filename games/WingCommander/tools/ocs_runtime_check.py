#!/usr/bin/env python3
"""Reject preload data, wrong relocations, bad chains and wrong slave helpers."""
import argparse
import json
from pathlib import Path
from ocs_runtime import BASE, SIZES, locate


def check(path):
    memory = path.read_bytes()
    layout = locate(memory)
    h0, h1, h2, h3 = layout['hunks']
    cases = {'segment size': h0-8, 'segment link': h1-4,
             'startup entry relocation': h0+5, 'A4 relocation': h3+0x14d5,
             'slave helper': h0+0x272b7, 'independent helper': h0+0x26a41,
             'slave header': layout['slave']+4}
    rejected = []
    for name, address in cases.items():
        bad = bytearray(memory)
        bad[address-BASE] ^= 1
        try:
            locate(bad)
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError('accepted '+name)
    # Keep archive/preload data intact; remove only the actual live code.
    bad = bytearray(memory)
    bad[h0-BASE:h0-BASE+SIZES[0]] = bytes(SIZES[0])
    try:
        locate(bad)
    except ValueError:
        rejected.append('preload-only memory')
    else:
        raise AssertionError('accepted preload copy')
    return dict(passed=True, layout=layout, rejected=rejected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.snapshot), indent=2))
