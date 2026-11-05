#!/usr/bin/env python3
"""Check fall/impulse displacement and local 90-ms age/decay from guest probes.

The oracle advances one native 5-ms unit at a time; the guest uses boundary-split
20-ms chunks. Require actual activity: an uneventful route cannot pass this audit.
"""
import argparse
from pathlib import Path
import re
import struct


def force_state(path):
    data=path.read_bytes()
    worlds=[m.start() for m in re.finditer(b'PDW20T01',data)
            if struct.unpack_from('>H',data,m.start()+8)[0]==1]
    assert len(worlds)==1
    forces=[m.start() for m in re.finditer(b'PDW20F01',data)
            if 0<m.start()-worlds[0]<4096]
    assert len(forces)==1
    return list(struct.unpack_from('>6H5I',data,forces[0]+8))


def signed(n):
    return ((n & 65535) ^ 32768) - 32768


def fraction(velocity, remainder):
    n = velocity + remainder
    q = (abs(n) // 18) * (-1 if n < 0 else 1)
    return q, n - q * 18


def word_add(register, delta):
    return (register & ~65535) | ((register + delta) & 65535)


def fall(v):
    result = v.copy()
    age, phase, remainder = v[6], v[16], signed(v[17])
    displacement = advances = 0
    # At entry the native guard has already accepted this age. Above 50 it
    # necessarily permits unlimited fall. A crossing from 50 requires its flag.
    for unit in range(4):
        if age > 50 and v[6] <= 50:
            assert len(v) == 28, 'Age-50 crossing needs an explicit native eligibility flag probe'
            if signed(v[27]) >= 0:
                break
        q, remainder = fraction(signed(2 * age), remainder)
        displacement += q
        phase += 1
        if phase == 18:
            age = (age + 1) & 0xffffffff
            phase = 0
            advances += 1
    result[1] = word_add(v[1] & ~65535, (v[1] * 2) & 65535)
    result[3] = word_add(v[3], -displacement)
    result[6], result[16], result[17] = age, phase, remainder & 65535
    result[23] += 1
    result[24] += advances
    return result[:27], advances


def impulse(v):
    result = v.copy()
    active, age, limit = v[10:13]
    velocity = list(map(signed, v[13:16]))
    phase = v[18]
    remainder = list(map(signed, v[19:22]))
    displacement = [0, 0, 0]
    advances = 0
    for unit in range(4):
        if not active:
            break
        for axis in range(3):
            q, remainder[axis] = fraction(velocity[axis], remainder[axis])
            displacement[axis] += q
        phase += 1
        if phase == 18:
            phase = 0
            age = (age + 1) & 65535
            if signed(age) >= signed(limit):
                active = 0
            velocity = [x >> 1 for x in velocity]
            advances += 1
    result[2:5] = [word_add(v[2+i], displacement[i]) for i in range(3)]
    result[10:12] = [active, age]
    result[13:16] = [x & 65535 for x in velocity]
    result[18:22] = [phase, *(x & 65535 for x in remainder)]
    result[25] += 1
    result[26] += advances
    return result[:27], advances


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('captures', type=Path, nargs='+')
p.add_argument('--require', choices=('fall', 'impulse', 'both'), default='both')
p.add_argument('--require-expiry',action='store_true')
p.add_argument('--require-three-axes',action='store_true')
a = p.parse_args()
for root in a.captures:
    pending_fall = pending_impulse = pending_reset = None
    falls = impulses = fall_ages = decays = resets = expiries = 0
    vectors=[]
    known_generations=set(); generation=None; generation_start=None
    previous_impulse=None; lifetime_units=[]
    previous_force=force_state(root/'code.bin')
    for field, off, values in re.findall(r'^PDFORCE_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
                                        (root/'swaps-gdb.txt').read_text(), re.M):
        off = int(off, 16)
        v = list(map(int, values.split()))
        assert len(v) in (27, 28)
        if pending_fall is None and pending_impulse is None and pending_reset is None:
            assert v[16:27]==previous_force, 'Force state changed outside observed integrator/reset hooks'
        if off == 0xcd5c:
            assert pending_fall is None
            pending_fall = v
        elif off == 0xcd64 and pending_fall is not None:
            expected, advances = fall(pending_fall)
            assert v[:27] == expected, (root.name, field, 'fall', [(i,x,y) for i,(x,y) in enumerate(zip(expected,v)) if x!=y])
            pending_fall = None
            falls += 1
            fall_ages += advances
        elif off == 0xcd96:
            assert pending_impulse is None and v[10]
            if generation==v[22] and previous_impulse is not None:
                assert previous_impulse[10] and v[10:16]==previous_impulse[10:16], 'Impulse state changed outside a recorded reset or decay'
                assert v[0]==previous_impulse[0]+4, 'An active impulse skipped a world step'
            else:
                generation=v[22]
                generation_start=v[0] if generation in known_generations else None
                if generation_start is not None:
                    assert v[11]==v[18]==0, 'A new impulse did not start at age/phase zero'
            pending_impulse = v
            vectors.append(list(map(signed,v[13:16])))
        elif off == 0xcdc4 and pending_impulse is not None:
            expected, advances = impulse(pending_impulse)
            assert v[:27] == expected, (root.name, field, 'impulse', [(i,x,y) for i,(x,y) in enumerate(zip(expected,v)) if x!=y])
            expiries += not v[10]
            if not v[10] and generation_start is not None:
                duration=v[0]-generation_start+4
                assert duration==18*v[12], 'Impulse lifetime disagrees with its native age limit'
                lifetime_units.append(duration)
            previous_impulse=v
            pending_impulse = None
            impulses += 1
            decays += advances
        elif off in (0xb390,0xc59e,0x9c8c,0xadba):
            assert pending_reset is None
            pending_reset = (off,v)
        elif off in (0xb398,0xc5a6,0x9c92,0xadc0):
            assert pending_reset is not None
            entry, before = pending_reset
            assert {0xb390:0xb398,0xc59e:0xc5a6,0x9c8c:0x9c92,0xadba:0xadc0}[entry] == off
            expected = before[:27]
            if entry in (0xb390,0xc59e):
                expected[6] = expected[16] = expected[17] = 0
            else:
                expected[18:22] = [0]*4
                expected[22] += 1
                known_generations.add(expected[22])
                if entry == 0x9c8c:
                    expected[11] = 0
                else:
                    expected[10] = 65535
            assert v[:27] == expected, (root.name, field, 'force reset', before, v)
            resets += 1
            pending_reset = None
        previous_force=v[16:27]
    unfinished=sum(x is not None for x in (pending_fall,pending_impulse,pending_reset))
    if not unfinished:
        assert force_state(root/'final-code.bin')==previous_force, 'Unobserved force mutation after final probe'
    ranges=[(min(v[i] for v in vectors),max(v[i] for v in vectors)) for i in range(3)] if vectors else []
    if a.require_expiry:
        assert lifetime_units, 'No complete unrefreshed impulse lifetime observed from a recorded reset'
    if a.require_three_axes:
        assert vectors and all(lo!=0 or hi!=0 for lo,hi in ranges), 'Missing nonzero impulse axis coverage'
    if a.require in ('fall','both'):
        assert falls >= 20 and fall_ages >= 4, 'Insufficient active falling/age coverage'
    if a.require in ('impulse','both'):
        assert impulses >= 20 and decays >= 4, 'Insufficient active impulse/decay coverage'
    print(f'{root.name}: {falls} fall steps / {fall_ages} age advances; '
          f'{impulses} impulse steps / {decays} decays; {resets} native resets verified; '
          f'{unfinished} unfinished probe pairs')
    print(f'  Impulse component ranges {ranges}; completed impulse expiries {expiries}; observed full lifetimes {[x*5 for x in lifetime_units]} ms')
