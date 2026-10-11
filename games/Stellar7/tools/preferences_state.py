#!/usr/bin/env python3
"""Validate real preferences and a nested native pause dialog (PREFERENCES_TEST)."""
import argparse
import json
import re
import struct
from pathlib import Path
from stellar7_report import locate


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    offset = int(re.search(r'^s60_preferences_results\s+00:([0-9A-F]+)',
                          listing.read_text(encoding='latin1'), re.M)[1], 16)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None
    at = base-meta['base']+offset
    signature = memory[at:at+4]
    assert signature in (b'PF60', b'PF61')
    names = ('stage', 'errors', 'entry_tick', 'entry_field', 'outer_last', 'outer_credit',
             'first_poll', 'nested_start', 'nested_end', 'return_field', 'return_last',
             'return_credit', 'return_tick', 'resumes_before', 'resumes_after',
             'nested_depth', 'nested_rendering', 'return_depth', 'return_rendering',
             'nested_last', 'nested_credit')
    result = dict(zip(names, struct.unpack_from('>2H11I6H2I', memory, at+4)))
    if signature == b'PF61':
        result.update(zip(('selections', 'setting_before', 'setting_after', 'option'),
                          struct.unpack_from('>4H', memory, at+72)))
    return result


def validate(r):
    if 'option' in r:
        assert 1 <= r['option'] <= 4 and r['selections'] == 1, r
        assert r['setting_before'] in (0, 1), r
        assert r['setting_after'] == r['setting_before'] ^ 1, r
    assert r['stage'] == 3 and r['errors'] == 0, r
    assert r['entry_tick'] == r['return_tick'], 'simulation advanced inside modal'
    assert r['entry_field'] <= r['outer_last'] <= r['first_poll']
    assert r['first_poll']+20 <= r['nested_start']
    assert r['nested_start']+30 <= r['nested_end'] <= r['return_last'] <= r['return_field']
    assert r['first_poll']+90 <= r['return_field']
    assert r['outer_credit'] > 0, 'fixture did not exercise preservation of existing debt'
    assert r['nested_credit'] == r['return_credit'] == r['outer_credit'], 'modal changed debt'
    assert r['nested_last'] == r['outer_last'], 'nested modal rebased the outer clock'
    assert r['resumes_after'] == (r['resumes_before']+1) & 0xffff
    assert (r['nested_depth'], r['nested_rendering']) == (1, 1)
    assert (r['return_depth'], r['return_rendering']) == (0, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
