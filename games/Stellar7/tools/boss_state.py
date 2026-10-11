#!/usr/bin/env python3
"""Read the native-callback oracle for fixed-rate boss enemy motion.

The guest compares XYZ, bank and pitch on every substep and full actor/RNG state after each
of four N-tick intervals. Cases cover all seven level handlers, height, bank, sideways movement and
type-7 pitch/acceleration. Eighteen coupled move-before-AI braking cases check native
distance and actor boundaries, including rollback of vector remainders.
Eight coupled curved-exit cases additionally check speed/pitch and spatial rollback/replay.
Allocation is stubbed; full encounters and curved trajectory pace need coverage.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    _, n = sim60_state.decode_version(struct.unpack_from('>H', memory, entry+50)[0])
    offset = struct.unpack_from('>H', memory, entry+88)[0]
    assert offset, 'BOSS_TEST fixture is absent'
    at = entry+offset
    signature = memory[at:at+4].decode('ascii')
    expected_cases = {'B760': 30, 'B761': 36, 'B762': 36, 'B763': 42, 'B764': 42, 'B765': 48, 'B766': 52, 'B767': 60}[signature]
    callback_cases = 34 if signature in ('B766', 'B767') else 30
    completed, failed = struct.unpack_from('>2H', memory, at+4)
    assert completed <= expected_cases
    cases = []
    for index in range(completed):
        kind, error, first, sixth, final = struct.unpack_from('>2H3i', memory, at+8+16*index)
        check = ('exit_rollback_replay' if signature == 'B767' and index >= 52
                 else 'coupled_native_braking' if index >= callback_cases else 'native_callback')
        failures = ([name for bit, name in enumerate(('rollback_position', 'replay_actor',
                     'replay_record', 'speed', 'pitch', 'rollback_rotation')) if error & (1 << bit)]
                    if check == 'exit_rollback_replay' else [])
        cases.append(dict(case=index, type=kind, failed=error, failure_checks=failures, check=check, axis="Z" if index >= callback_cases else "Y",
                          first_tick_position=first, midpoint_tick=(n+1)//2, midpoint_tick_position=sixth, final_position=final))
    return dict(tick_substeps=n, signature=signature, expected_cases=expected_cases, completed=completed,
                failed=failed, cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, indent=2))
        ok &= result['completed'] == result['expected_cases'] and result['failed'] == 0
        ok &= all(not c['failed'] for c in result['cases'])
    raise SystemExit(0 if ok else 1)
