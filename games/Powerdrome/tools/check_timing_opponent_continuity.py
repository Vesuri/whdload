#!/usr/bin/env python3
"""Audit a continuous opponent deadline across flight, rescue and flight return.

Checks 27-value PDPOPP events against independent pit/world snapshots. Requires
one completed rescue and subsequent flight updates by default. The repair-only mode
checks the same ledger/ownership invariants over the full directed repair route.
Does not certify complete
opponent state equivalence, native A500 calibration, or arbitrary mode exits.
"""
import argparse
import json
import re
import struct
from collections import Counter
from pathlib import Path


def check(root, flight_only=False, stable_lap_domain=False, repair_only=False):
    assert (root / "final-code.bin").is_file(), "Capture must be terminal"
    assert not (flight_only and repair_only)
    if repair_only:
        cfg = json.loads((root / "configuration.json").read_text())
        assert re.search(r"\bCUSTOM5=13\b", cfg["WHD_ARGS"])
        assert int(cfg["ANCHOR"], 0) == 0x148d0
    # Resolve the live repair wrappers. Older captures used a sampled native
    # offset (record +36); current builds use the continuous deadline (+20).
    # Require both start and expiry to read the same domain, in both snapshots.
    game = int((root/'game-base.txt').read_text(), 0)
    base = int((root/'dump-base.txt').read_text(), 0)
    repair_domains = []
    for prefix in ('', 'final-'):
        chip = (root/(prefix+'chip.bin')).read_bytes()
        code = (root/(prefix+'code.bin')).read_bytes()
        for offset, opcode in ((0xd4b6, b'\x2e\x28'), (0xd4fe, b'\x20\x28')):
            assert chip[game+offset:game+offset+2] == bytes.fromhex('4eb9')
            entry = struct.unpack_from('>I', chip, game+offset+2)[0]-base
            assert 0 <= entry < len(code)-24
            body = code[entry:entry+24]
            matches = [domain for domain in (20, 36)
                       if opcode+struct.pack('>H', domain) in body]
            assert len(matches) == 1, 'Unknown opponent repair clock wrapper'
            repair_domains.extend(matches)
    assert len(set(repair_domains)) == 1, 'Repair start/expiry clock domains differ'
    repair_deadlines = repair_domains[0] == 20
    lap_epoch = None
    if stable_lap_domain:
        game = int((root / "game-base.txt").read_text(), 0)
        base = int((root / "dump-base.txt").read_text(), 0)
        chip = (root / "chip.bin").read_bytes()
        before_code = (root / "code.bin").read_bytes()
        after_code = (root / "final-code.bin").read_bytes()
        frame = struct.unpack_from(">I", chip, game+0xca46)[0]-base
        lap = before_code.find(b"PDLAP001", frame, frame+16384)
        assert lap >= 0, "Stable lap diagnostics missing"
        lap_epoch, reset_count = [struct.unpack_from(">I", before_code, lap+i)[0] for i in (8, 24)]
        assert [struct.unpack_from(">I", after_code, lap+i)[0] for i in (8, 24)] == [lap_epoch, reset_count], "Lap epoch changed: use a capture with reset-boundary observations"
    if flight_only:
        cfg = json.loads((root / 'configuration.json').read_text())
        assert re.search(r'\bCUSTOM5=8\b', cfg['WHD_ARGS']) and int(cfg['FIELDS']) == 300
    pit = origin = initial_phase = before = flight_before = None
    entered = returned = None
    samples = restores = flight_restores = post_updates = world_restores = 0
    clocks = Counter()
    latest = None
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDPIT_EVENT':
            pit = (int(v[1]), int(v[2], 16), list(map(int, v[3:])))
        if v[0] != 'PDPOPP_EVENT':
            continue
        field, off = int(v[1]), int(v[2], 16)
        t = list(map(int, v[3:]))
        assert len(t) == 27, 'Continuous deadline/ownership diagnostics missing'
        assert pit[:2] == (field, off)
        p = pit[2]
        if not t[0]:
            assert origin is None, 'Opponent timeline reset within race'
            continue
        if origin is None:
            origin, initial_phase = t[13], t[23]
        assert (t[13], t[23]) == (origin, initial_phase), 'Pit changed opponent epoch/phase'
        assert 0 <= t[8] <= t[7] and t[2] == t[7] - t[8]
        assert t[4] - origin + 18 == t[7] * 18 + t[6], 'Elapsed opponent time lost or duplicated'
        assert t[5] == origin + t[8] * 18, 'Deadline skipped or repeated'
        assert t[3] == (initial_phase + t[8]) & 65535, 'Counter phase not continuous'
        if latest is not None:
            assert t[4] >= latest[4] and t[7] >= latest[7] and t[8] >= latest[8]
        latest = t
        if off == 0x103a2:
            assert entered is None and p[0] == 1 and t[24] == 0
            entered = (p.copy(), t.copy())
        if off == 0xe3bc and p[0]:
            assert before is None and not t[1]
            before = t.copy()
        if off == 0xe3c4 and before is not None:
            assert t[1] == t[2] == t[22] == 0
            assert t[17:19] == before[17:19], 'Pit presentation RNG/counter not restored'
            if repair_only:
                owed = (t[4] - origin) // 18 + 1
                assert t[8] == min(owed, before[8]+32), 'Repair service lost scheduled opponent work'
            restores += 1
            before = None
        if off == 0xced8 and t[24] and not p[1]:
            assert flight_before is None
            flight_before = t.copy()
        if off == 0xd3de and flight_before is not None and t[8] == flight_before[8]:
            assert t[17] == flight_before[17], 'Opponent begin replaced the live world RNG'
        if t[1]:
            assert t[2] > 0 and t[15] == 18 and t[18] == t[3]
            assert t[22] == (not t[24]), 'Wrong RNG owner for flight/pit update'
            assert t[9] == (t[5] + t[14]) & 0xffffffff
            if off == 0xd56c:
                samples += 1
                if returned is not None and t[24]:
                    post_updates += 1
            register = {0xd4bc: 20, 0xd504: 19, 0xd7fe: 20,
                        0xd83c: 20, 0xd86c: 20}.get(off)
            if register is not None:
                expected = t[5] if repair_deadlines and off in (0xd4bc, 0xd504) else t[9]
                if lap_epoch is not None and off in (0xd7fe, 0xd83c, 0xd86c):
                    expected = (lap_epoch+t[5]-origin+18) & 0xffffffff
                assert t[register] == expected, f'Incorrect logical clock at {off:#x}'
                clocks[off] += 1
        if off == 0xce28:
            assert entered is not None and returned is None and before is None
            assert t[1] == t[2] == t[21] == t[22] == 0
            assert t[4] == p[6] and 0 <= t[6] < 18
            assert t[8] == (p[6] - origin) // 18 + 1
            assert t[5] > p[6]
            returned = (p.copy(), t.copy())
            print(f'{root.name}: pit return: {t[8]} session updates; '
                  f'{t[6] * 5} ms residual, phase {t[3]} preserved')
        if off == 0xcedc and flight_before is not None:
            world_restores += 1
            assert t[1] == t[2] == t[22] == 0
            assert t[18] == flight_before[18], 'Player world counter not restored'
            assert t[4] == t[25], 'Flight allocation did not reach world time'
            # One flight call serves at most 32 owed updates. Initial-pit or
            # stalled-render backlog remains explicit instead of vanishing.
            owed = (t[25] - origin) // 18 + 1
            assert t[8] == min(owed, flight_before[8]+32), 'Incorrect bounded flight service'
            assert t[6] == t[25]-origin+18-t[8]*18, 'Flight lost retained opponent debt'
            if t[8] == flight_before[8]:
                assert t[17] == flight_before[17], 'No-update call changed RNG'
            if returned is not None and post_updates and flight_restores == 0:
                old = returned[1]
                elapsed = t[4] - old[4]
                assert (t[8] - old[8]) * 18 + t[6] == elapsed + old[6]
                print(f'  First resumed allocation: {elapsed * 5} ms after cutoff + '
                      f'{old[6] * 5} ms residual = {(t[8] - old[8]) * 90} ms served '
                      f'+ {t[6] * 5} ms residual')
            if returned is not None and post_updates:
                flight_restores += 1
            flight_before = None
    assert origin is not None and samples
    if repair_only:
        assert restores >= 264 and clocks, "Need complete repair service and exercised clock readers"
        assert before is None and flight_before is None, "Incomplete service boundary"
    else:
        assert world_restores >= 10
    if repair_only:
        print("  Repair-window ledger/ownership only; no rescue-return or input-consumption claim")
    elif flight_only:
        assert entered is None and returned is None
    else:
        assert entered and returned and restores and flight_restores >= 10
        assert post_updates >= 4 and clocks
    print(f'  {samples} scheduled movement samples; {post_updates} after return; '
          f'{restores} pit and {world_restores} world counter restores ({flight_restores} after return)')
    print('  Logical clock results: ' + ', '.join(f'{k:#x}={v}' for k, v in sorted(clocks.items())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    parser.add_argument('--flight-only', action='store_true',
                        help='Check the bounded 300-field CUSTOM5=8 pause route without requiring a pit')
    parser.add_argument("--stable-lap-domain", action="store_true",
                        help="Check lap reads against the retained logical epoch; repair domain follows the installed wrappers")
    parser.add_argument("--repair-only", action="store_true",
                        help="Check the full CUSTOM5=13 repair window without requiring rescue or flight")
    args = parser.parse_args()
    for capture in args.captures:
        check(capture, args.flight_only, args.stable_lap_domain, args.repair_only)
