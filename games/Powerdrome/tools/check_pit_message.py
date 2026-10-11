#!/usr/bin/env python3
"""Check native pit-message publication against the owning counter domain.

Read-only field captures must probe D8CA (entry), D8D0 (after MOVE), D8D8
(after ADD #30), and E2A6 (outer expiry reader). Default mode requires full
register/SP observations. --expect-leak diagnoses the original WORLD20 build,
whose older capture need not contain the intermediate/register probes.
Debugger SR is deliberately not used as evidence of guest condition flags.
"""
import argparse
import json
from pathlib import Path


def events(root):
    assert (root / 'final-code.bin').is_file(), 'Capture must have finished'
    result = []
    current = None
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'PDTIME_EVENT':
            current = {'field': int(parts[1]), 'off': int(parts[2], 16)}
            result.append(current)
        elif parts[0] in ('PDMESSAGE_EVENT', 'PDPOPP_EVENT', 'PDMREG_EVENT'):
            assert current is not None
            assert (int(parts[1]), int(parts[2], 16)) == (current['field'], current['off'])
            current[parts[0]] = list(map(int, parts[3:]))
    return result


def check(root, expect_leak=False):
    config = json.loads((root / 'configuration.json').read_text())
    assert int(config['ANCHOR'], 0) == 0xd8ca
    pending = None
    checked = redirected = intermediate = consumers = 0
    last_publication = None
    for event in events(root):
        off = event['off']
        if off == 0xd8ca:
            assert pending is None, 'Publication did not reach its native continuation'
            message = event['PDMESSAGE_EVENT']
            opponent = event['PDPOPP_EVENT']
            assert len(message) == 8 and len(opponent) == 27
            assert message[0] == opponent[18]
            external = opponent[1] != 0 and opponent[24] == 0
            target = opponent[10] if external else message[0]
            if not expect_leak:
                assert len(event['PDMREG_EVENT']) == 19
            pending = (event, target, external)
        elif off in (0xd8d0, 0xd8d8) and pending is not None:
            before, target, external = pending
            old = before['PDMESSAGE_EVENT']
            new = event['PDMESSAGE_EVENT']
            source = old[0] if expect_leak else target
            expected = (source + (30 if off == 0xd8d8 else 0)) & 0xffffffff
            assert new[1] == expected, (root, event['field'], new[1], expected)
            assert (new[0], new[2], new[7]) == (old[0], old[2], old[7]), 'Counter, message pointer or SP changed'
            if not expect_leak:
                registers = event['PDMREG_EVENT']
                assert registers[:16] == before['PDMREG_EVENT'][:16], 'Native D/A registers or SP changed'
                assert registers[17:] == before['PDMREG_EVENT'][17:], 'Movement delta or speed changed'
            if off == 0xd8d0:
                intermediate += 1
            else:
                checked += 1
                redirected += int(external and target != old[0])
                last_publication = (new[1], target)
                pending = None
        elif off == 0xe2a6 and last_publication is not None:
            message = event['PDMESSAGE_EVENT']
            deadline, target = last_publication
            if message[1] == deadline:
                assert message[0] >= target, 'Outer counter moved backwards without a recorded reset'
                consumers += 1
            last_publication = None
    assert pending is None, 'Trailing publication is incomplete'
    assert checked and redirected and consumers, 'Need publication, differing counter domains and an outer consumer'
    if not expect_leak:
        assert intermediate == checked, 'Missing intermediate MOVE boundary'
    label = 'original counter leak reproduced' if expect_leak else 'outer deadline and register/SP contracts pass'
    print(f'{root.name}: {label}; {checked} complete publications, '
          f'{redirected} differing-domain cases, {consumers} following outer readers')
    if not expect_leak:
        print('Guest CCR runtime coverage and elapsed-time message expiry remain separate checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--expect-leak', action='store_true')
    args = parser.parse_args()
    check(args.capture, args.expect_leak)


if __name__ == '__main__':
    main()
