#!/usr/bin/env python3
"""Verify rescue message deadline conversion at the first resumed world update.

Read-only probes: 14090, 140d0, ce28, ca3e, ca4a, 13536, 1353c,
13558, da54, da5a, da64. --expect-leak diagnoses the old domain mismatch.
The route must start after rescue acceptance and include the departure publisher.
"""
import argparse
from pathlib import Path
from check_flight_message import read, registers_equal, phase as message_phase


def signed(value):
    return value if value < 0x80000000 else value - 0x100000000


def check(root, expect_leak=False, inactive=False):
    pending = publication = returned = start = handoff = compare = retune = None
    publications = transitions = comparisons = clears = 0
    clearing = False
    last_phase = None
    for row in read(root):
        off, msg, domain = row['off'], row['PDMESSAGE_EVENT'], row['domain']
        assert len(msg) == len(domain) == 8
        if handoff is not None:
            last_phase = message_phase(row)
        if off == 0x14090:
            retune = row
        if inactive and handoff is not None:
            assert domain[5] == 0, 'Inactive deadline revived before a new publisher'
        if off == 0x13536:
            if handoff is not None:
                # A new publication replaces the rescued message; its lifetime
                # belongs to the ordinary-flight checker, not this handoff.
                break
            assert pending is None
            pending = row
        elif off == 0x1353c:
            assert pending is not None
            if pending['domain'][1] and pending['domain'][4]:
                source = pending['PDPOPP_EVENT'][10]
            else:
                source = pending['PDMESSAGE_EVENT'][0]
            assert msg[1] == source
            registers_equal(pending, row)
        elif off == 0x13558:
            assert pending is not None and pending['domain'][1] == 1
            source = pending['PDPOPP_EVENT'][10] if pending['domain'][4] else pending['PDMESSAGE_EVENT'][0]
            assert msg[1] == source + 45
            registers_equal(pending, row)
            publication = row
            publications += 1
            pending = None
        elif off == 0xce28:
            assert domain[:2] == [0, 0]
            if inactive:
                assert publication is None and retune is not None
                assert retune['domain'][5] == domain[5] == 0
                assert msg[1] == retune['PDMESSAGE_EVENT'][1]
            else:
                assert publication is not None
                assert msg[1] == publication['PDMESSAGE_EVENT'][1]
            returned = row
        elif off == 0xca3e and returned is not None and handoff is None:
            assert domain[:2] == [0, 0]
            start = row
        elif off == 0xca4a and start is not None and handoff is None:
            assert domain[:3] == [1, 0, 1]
            old = start['PDMESSAGE_EVENT']
            assert old[1] == returned['PDMESSAGE_EVENT'][1]
            remaining = signed((old[1] - old[0]) & 0xffffffff)
            phase = message_phase(row)
            target = 0xffffffff if old[1] == 0xffffffff else (phase + remaining) & 0xffffffff
            assert target != old[1], 'Fixture did not exercise different clock domains'
            assert msg[1] == (old[1] if expect_leak else target)
            assert msg[0] == phase and msg[2] == old[2]
            registers_equal(start, row)
            handoff = (msg[1], phase, remaining, domain[5] != 0)
            transitions += 1
            print(f'  handoff: outer={old[0]}, phase={phase}, deadline={old[1]} -> {msg[1]}, remaining={remaining}, message_active={domain[5] != 0}')
        elif off == 0xda54 and handoff is not None:
            assert compare is None
            assert domain[:2] == [1, 0]
            assert msg[1] == handoff[0], 'Unexpected publication/rebase before expiry'
            compare = row
        elif off in (0xda5a, 0xda64) and compare is not None:
            deadline = signed(compare['PDMESSAGE_EVENT'][1])
            phase = message_phase(compare)
            expired = deadline <= phase
            assert off == (0xda5a if expired else 0xda64)
            registers_equal(compare, row)
            comparisons += 1
            clearing = expired
            if expired:
                print(f'  expiry: phase={phase}, elapsed phases={phase-handoff[1]}')
                assert not expect_leak and phase >= handoff[1] + handoff[2]
            compare = None
        elif off == 0xda64 and clearing:
            assert domain[5] == 0, 'Native clear did not retire the message'
            clears += 1
            clearing = False
    assert transitions == 1 and handoff is not None
    assert (publications == 0 and not handoff[3]) if inactive else publications > 0
    assert pending is None and compare is None and not clearing
    if handoff[3]:
        assert comparisons and last_phase >= handoff[1] + handoff[2]
        assert clears == (0 if expect_leak else 1)
    print(f'{root.name}: {publications} pit publications, one paired transition, {comparisons} expiry branch/register checks, {clears} clears')
    print('  ' + ('Clock-domain leak reproduced' if expect_leak else 'Remaining count ownership verified') + '; native pit-duration calibration, sentinels, wrap and other exits remain separate')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--expect-leak', action='store_true')
    p.add_argument('--inactive', action='store_true', help='Require an already inactive deadline observed at retune, with no pit publication')
    a = p.parse_args()
    check(a.capture, a.expect_leak, a.inactive)
