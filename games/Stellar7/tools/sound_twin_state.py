#!/usr/bin/env python3
"""Read the SOUND_TWIN record (src/sound60_test.s) from a capture snapshot.

  python3 tools/sound_twin_state.py CAPTURE --listing EXACT.lst [--snapshot DIR] [--expect-errors]

DIR defaults to the capture's last tick checkpoint (else the capture itself). The check
passes when calls were compared, written Paula words were observed and every error
counter is zero; --expect-errors inverts that for the SOUND_TWIN_BAD negative control.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys

from stellar7_report import locate

FIELDS = ('calls', 'compared', 'skipped', 'state_errors', 'write_errors', 'real_errors',
          'reference_errors', 'written', 'first_call')
KINDS = {0: None, 1: 'state', 2: 'write', 3: 'real', 4: 'reference'}


def read(capture, listing, snapshot=None):
    capture, listing = Path(capture), Path(listing)
    binary = (capture/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    offset = int(re.search(r'^s60_test_sound_record\s+00:([0-9A-F]+)',
                           listing.read_text(encoding='latin1'), re.M)[1], 16)
    if snapshot is None:
        checkpoints = sorted((capture/'checkpoints').glob('*'), key=lambda p: int(p.name)) \
            if (capture/'checkpoints').exists() else []
        snapshot = checkpoints[-1] if checkpoints else capture
    snapshot = Path(snapshot)
    base = int(re.search(r'^base=(\S+)', (capture/'anchor.txt').read_text(), re.M)[1], 0)
    memory = (snapshot/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    slave = locate(memory, binary[32:32+size], base, header=32)
    assert slave is not None, 'slave not found in snapshot'
    at = slave-base+offset
    assert memory[at:at+4] == b'ST60', 'SOUND_TWIN record missing'
    result = dict(zip(FIELDS, struct.unpack_from('>9I', memory, at+4)))
    kind, index, native, replacement = struct.unpack_from('>4H', memory, at+40)
    result['first'] = None if not kind else dict(
        call=result['first_call'], kind=KINDS.get(kind, kind), index=index,
        native=f'${native:04x}', replacement=f'${replacement:04x}')
    del result['first_call']
    result['snapshot'] = str(snapshot)
    return result


def errors(result):
    return sum(result[k] for k in ('state_errors', 'write_errors', 'real_errors', 'reference_errors'))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('capture')
    parser.add_argument('--listing', required=True)
    parser.add_argument('--snapshot')
    parser.add_argument('--expect-errors', action='store_true')
    args = parser.parse_args()
    result = read(args.capture, args.listing, args.snapshot)
    if args.expect_errors:
        result['passed'] = errors(result) > 0 and result['first'] is not None
    else:
        result['passed'] = (result['compared'] > 0 and result['written'] > 0
                            and errors(result) == 0 and result['first'] is None)
    print(json.dumps(result, indent=1))
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
