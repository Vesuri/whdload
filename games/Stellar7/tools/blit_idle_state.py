#!/usr/bin/env python3
"""Read the BLIT_IRQ_IDLE counters (src/blit60.s) from a VERIFY capture snapshot.

  python3 tools/blit_idle_state.py CAPTURE --listing EXACT.lst [--snapshot DIR]

DIR defaults to the capture's last tick checkpoint (else the capture itself). The check
passes when field callbacks ran, the enable was masked at least once and Kickstart's
blit queue was never found active (no busy or restored field). Any queued Kickstart
blit enables INTENA BLIT itself, so a later mask would count again.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys

from stellar7_report import locate

FIELDS = ('fields', 'masks', 'busy', 'restored')


def read(capture, listing, snapshot=None):
    capture, listing = Path(capture), Path(listing)
    binary = (capture/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    offset = int(re.search(r'^s60_test_blit_record\s+00:([0-9A-F]+)',
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
    assert memory[at:at+4] == b'BI60', 'BLIT_IRQ_IDLE record missing'
    result = dict(zip(FIELDS, struct.unpack_from('>4I', memory, at+4)))
    result['snapshot'] = str(snapshot)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('capture')
    parser.add_argument('--listing', required=True)
    parser.add_argument('--snapshot')
    args = parser.parse_args()
    result = read(args.capture, args.listing, args.snapshot)
    result['passed'] = (result['fields'] > 0 and result['masks'] > 0
                        and result['busy'] == 0 and result['restored'] == 0)
    print(json.dumps(result, indent=1))
    sys.exit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
