#!/usr/bin/env python3
"""Check supported flight message publication and expiry counter ownership.

Requires the complete MOVE and CMP/branch boundaries. --require-wrap requires
an unrefreshed message to expire across a native word-phase rollover. Session
resets, other publishers and guest CCR arithmetic are separate contracts.
"""
import argparse
from pathlib import Path
from check_pit_message import events


def read(root):
    rows = events(root)
    domains = []
    phases = []
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if v and v[0] == 'PDMSGPHASE_EVENT':
            phases.append((int(v[1]), int(v[2],16), list(map(int,v[3:]))))
        if v and v[0] == 'PDMSGDOMAIN_EVENT':
            domains.append((int(v[1]), int(v[2], 16), list(map(int, v[3:]))))
    relevant = [r for r in rows if 'PDMESSAGE_EVENT' in r]
    assert len(relevant) == len(domains)
    for row, (field, off, values) in zip(relevant, domains):
        assert (row['field'], row['off']) == (field, off)
        row['domain'] = values
    if phases:
        assert len(phases) == len(relevant)
        for row, (field, off, values) in zip(relevant, phases):
            assert (row['field'], row['off']) == (field,off) and len(values)==3
            row['message_phase'] = values
    return relevant


def phase(row):
    if 'message_phase' in row:
        valid, low, extended = row['message_phase']
        assert valid == 1 and low == row['domain'][3] == (extended & 65535)
        return extended
    return row['domain'][3]


def registers_equal(a, b):
    old, new = a['PDMREG_EVENT'], b['PDMREG_EVENT']
    assert len(old) == len(new) == 19
    assert old[:16] == new[:16] and old[17:] == new[17:], 'Native registers/SP or movement state changed'


def check(root, require_wrap=False):
    pending = compare = publication = clearing = None
    published = redirected = comparisons = restored = clears = 0
    expiry_ages = []
    last_phase = None
    wrapped_expiries = 0
    for row in read(root):
        off, msg, domain = row['off'], row['PDMESSAGE_EVENT'], row['domain']
        assert len(domain) == 8
        if domain[0:2] == [1, 0] and domain[6:] == [0, 65535]:
            current_phase = phase(row)
            assert last_phase is None or current_phase >= last_phase, 'Message-clock reset needs a separate contract'
            if last_phase is not None:
                assert current_phase-last_phase == ((domain[3]-(last_phase & 65535)) & 65535), 'Unexplained extended-clock epoch jump'
            last_phase = current_phase
        if off in (0x13536, 0x1353c, 0x13558, 0xda54):
            assert domain[0:2] == [1, 0] and domain[6:] == [0, 65535], 'Capture left supported human flight'
        if off == 0x13536:
            assert pending is None
            pending = row
        elif off == 0x1353c:
            assert pending is not None and msg[1] == phase(pending)
            registers_equal(pending, row)
            restored += 1
        elif off == 0x13558:
            assert pending is not None
            assert msg[1] == phase(pending)+45
            registers_equal(pending, row)
            assert msg[0] == pending['PDMESSAGE_EVENT'][0], 'Publisher changed the outer counter'
            published += 1
            redirected += msg[0] != phase(pending)
            publication = (msg[1], phase(pending))
            pending = None
        elif off == 0xda54:
            assert compare is None
            compare = row
        elif off in (0xda5a, 0xda64) and compare is not None:
            old = compare['PDMESSAGE_EVENT']
            counter = phase(compare)
            # Word-phase wrap is extended by the message clock. This route does
            # not reset or wrap the extended signed-positive domain.
            expired = old[1] <= counter
            assert off == (0xda5a if expired else 0xda64), 'Expiry branch used the wrong counter domain'
            registers_equal(compare, row)
            comparisons += 1
            if expired:
                assert publication is not None and publication[0] == old[1], 'Unobserved message publisher'
                assert counter >= publication[1]+45
                expiry_ages.append(counter-publication[1])
                wrapped_expiries += (counter >> 16) > (publication[1] >> 16)
                clearing = publication
            compare = None
        elif off == 0xda64 and clearing is not None:
            assert domain[5] == 0, 'Expired message was not cleared by the native helper'
            clears += 1
            clearing = None
    assert pending is None and compare is None and clearing is None
    assert published == restored and redirected and comparisons and clears
    assert clears == len(expiry_ages)
    if require_wrap:
        assert wrapped_expiries, "No unrefreshed message expired across a word-phase rollover"
    print(f"  Expiries crossing a 16-bit phase rollover: {wrapped_expiries}")
    print(f'{root.name}: {published} logical publications ({redirected} different from the render counter), {comparisons} expiry branch/register checks')
    print(f'  {clears} native clears; observed ages in 90-ms phases: {expiry_ages}')
    print('  Native A500 duration calibration, resets/32-bit wrap, other publishers and full mode lifecycles remain separate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--require-wrap', action='store_true')
    args = parser.parse_args()
    check(args.capture, args.require_wrap)
