#!/usr/bin/env python3
"""Check supported flight message publication and expiry counter ownership.

Requires the complete MOVE and CMP/branch boundaries. Native phase wrap, lap
rebasing, other publishers and guest CCR arithmetic are separate contracts.
"""
import argparse
from pathlib import Path
from check_pit_message import events


def read(root):
    rows = events(root)
    domains = []
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if v and v[0] == 'PDMSGDOMAIN_EVENT':
            domains.append((int(v[1]), int(v[2], 16), list(map(int, v[3:]))))
    relevant = [r for r in rows if 'PDMESSAGE_EVENT' in r]
    assert len(relevant) == len(domains)
    for row, (field, off, values) in zip(relevant, domains):
        assert (row['field'], row['off']) == (field, off)
        row['domain'] = values
    return relevant


def registers_equal(a, b):
    old, new = a['PDMREG_EVENT'], b['PDMREG_EVENT']
    assert len(old) == len(new) == 19
    assert old[:16] == new[:16] and old[17:] == new[17:], 'Native registers/SP or movement state changed'


def check(root):
    pending = compare = publication = clearing = None
    published = redirected = comparisons = restored = clears = 0
    expiry_ages = []
    last_phase = None
    for row in read(root):
        off, msg, domain = row['off'], row['PDMESSAGE_EVENT'], row['domain']
        assert len(domain) == 8
        if domain[0:2] == [1, 0] and domain[6:] == [0, 65535]:
            assert last_phase is None or domain[3] >= last_phase, 'Phase reset/wrap needs a separate contract'
            last_phase = domain[3]
        if off in (0x13536, 0x1353c, 0x13558, 0xda54):
            assert domain[0:2] == [1, 0] and domain[6:] == [0, 65535], 'Capture left supported human flight'
        if off == 0x13536:
            assert pending is None
            pending = row
        elif off == 0x1353c:
            assert pending is not None and msg[1] == pending['domain'][3]
            registers_equal(pending, row)
            restored += 1
        elif off == 0x13558:
            assert pending is not None
            assert msg[1] == pending['domain'][3]+45
            registers_equal(pending, row)
            assert msg[0] == pending['PDMESSAGE_EVENT'][0], 'Publisher changed the outer counter'
            published += 1
            redirected += msg[0] != pending['domain'][3]
            publication = (msg[1], pending['domain'][3])
            pending = None
        elif off == 0xda54:
            assert compare is None
            compare = row
        elif off in (0xda5a, 0xda64) and compare is not None:
            old = compare['PDMESSAGE_EVENT']
            counter = compare['domain'][3]
            # This bounded route never wraps/rebases its logical phase.
            expired = old[1] <= counter
            assert off == (0xda5a if expired else 0xda64), 'Expiry branch used the wrong counter domain'
            registers_equal(compare, row)
            comparisons += 1
            if expired:
                assert publication is not None and publication[0] == old[1], 'Unobserved message publisher'
                assert counter >= publication[1]+45
                expiry_ages.append(counter-publication[1])
                clearing = publication
            compare = None
        elif off == 0xda64 and clearing is not None:
            assert domain[5] == 0, 'Expired message was not cleared by the native helper'
            clears += 1
            clearing = None
    assert pending is None and compare is None and clearing is None
    assert published == restored and redirected and comparisons and clears
    assert clears == len(expiry_ages)
    print(f'{root.name}: {published} logical publications ({redirected} different from the render counter), {comparisons} expiry branch/register checks')
    print(f'  {clears} native clears; observed ages in 90-ms phases: {expiry_ages}')
    print('  Native A500 duration calibration, lap/reset/wrap, other publishers and full mode lifecycles remain separate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    check(parser.parse_args().capture)
