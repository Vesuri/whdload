#!/usr/bin/env python3
"""Check curved exit positions against an independent rational velocity model.

Native table rounding is retained. Within each substep, native projected endpoint
velocities define a linear function of legacy-interval phase, centered at 1/2 to
preserve move-before-AI pace. Integrate that function with exact rational arithmetic.
The accumulated published integer position must stay within one world unit on
every axis. This checks the specified continuous path, not equality to the coarse
native curved path or general encounter behavior.
"""
import argparse
import json
import re
import struct
from fractions import Fraction
from pathlib import Path
import boss_state
from check_disabled import hunks
from stellar7_report import GAME, locate


def word(value):
    return (value + 32768) % 65536 - 32768


def inspect(folder, listing, omit_acceleration=False):
    folder, listing = Path(folder), Path(listing)
    fixture = boss_state.read(folder)
    n = fixture['tick_substeps']
    assert fixture['signature'] == 'B767' and fixture['completed'] == 60 and fixture['failed'] == 0
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = {name: int(value, 16) for name, value in re.findall(
        r'^(\w+)\s+00:([0-9A-F]+)', listing.read_text(encoding='latin1'), re.M)}
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None
    origin = base-meta['base']
    at = origin+symbols['s60_boss_path_results']
    assert memory[at:at+4] == b'BP60'
    cases, ticks = struct.unpack_from('>2H', memory, at+4)
    assert (cases, ticks) == (8, 4*n)
    starts = [struct.unpack_from('>3h', memory, origin+symbols['s60_boss_exit_cases']+6*i)
              for i in range(cases)]
    positions = struct.unpack_from('>'+str(cases*ticks*3)+'i', memory, at+8)
    code = hunks(GAME)[0][0]
    table = struct.unpack_from('>I', code, 0x16aac)[0]
    assert table == 0x14e88
    loaded_table = meta['code']-meta['base']+table
    assert memory[loaded_table:loaded_table+4098] == code[table:table+4098]
    # Original state-4 increments and the turn-helper argument.
    pitch_step = struct.unpack_from('>H', code, 0x115aa)[0]
    assert struct.unpack_from('>H', code, 0x115b0)[0] == 0x7032
    speed_step = 50
    turn_step = struct.unpack_from('>H', code, 0x115b8)[0]
    assert (pitch_step, turn_step) == (144, 256)

    def cosine(angle):
        index = (angle & 65535) >> 4
        if index & 2048:
            index = 4096-index
        return struct.unpack_from('>h', code, table+2*index)[0]

    def vector(speed, pitch, yaw):
        cp, sp = cosine(pitch), cosine(pitch-16384)
        cy, sy = cosine(yaw), cosine(yaw-16384)
        # Native two-stage fixed-point multiplication rounds down at each shift.
        return (((-cp*speed) >> 14)*sy >> 14,
                ((cp*speed) >> 14)*cy >> 14, sp*speed >> 14)

    failures, maximum = [], Fraction(0)
    for case, (initial_speed, initial_yaw, initial_pitch) in enumerate(starts):
        exact = [Fraction(0), Fraction(0), Fraction(0)]
        for tick in range(1, ticks+1):
            interval, phase = divmod(tick-1, n)
            speed = word(initial_speed+speed_step*interval)
            pitch = word(initial_pitch+pitch_step*(tick-1)//n)
            # The first native AI call sets turn velocity after movement.
            yaw = word(initial_yaw+turn_step*(tick-1)//n)
            before = vector(speed, pitch, yaw)
            after = vector(word(speed+speed_step), pitch, yaw)
            lower, upper = Fraction(phase, n)-Fraction(1, 2), Fraction(phase+1, n)-Fraction(1, 2)
            for axis in range(3):
                integral = Fraction(before[axis], n)
                if not omit_acceleration:
                    integral += (after[axis]-before[axis])*(upper*upper-lower*lower)/2
                exact[axis] += integral
                observed = positions[(case*ticks+tick-1)*3+axis]
                error = abs(observed-exact[axis])
                maximum = max(maximum, error)
                if error >= 1:
                    failures.append(dict(case=case, tick=tick, axis=('X','Z','Y')[axis],
                                         observed=observed, expected=str(exact[axis]), error=str(error)))
    return dict(tick_substeps=n, cases=cases, ticks_per_case=ticks, checked_coordinates=cases*ticks*3,
                maximum_error=str(maximum), failed_coordinates=len(failures), failures=failures)


def validate(result):
    assert result['checked_coordinates'] == 8*4*result['tick_substeps']*3 and not result['failed_coordinates'], result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
