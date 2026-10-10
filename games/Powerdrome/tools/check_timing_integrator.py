#!/usr/bin/env python3
"""Verify carried scalar/vector fractions from independent guest movement probes.

The default oracle requires centering off. --centering additionally checks the native
strength/mode/modifier adjustment against explicit guest input-state probes.
It verifies arithmetic and saved positions, not collision/fall/impulse timing.
"""
import argparse
from pathlib import Path
import re
import struct


def signed16(n):
    return ((n & 65535) ^ 32768) - 32768


def initial_remainders(path):
    data = path.read_bytes()
    worlds = [m.start() for m in re.finditer(b'PDW20T01', data)
              if struct.unpack_from('>H', data, m.start() + 8)[0] == 1]
    assert len(worlds) == 1
    hits = [m.start() for m in re.finditer(b'PDW20I01', data)
            if 0 < m.start() - worlds[0] < 2048]
    assert len(hits) == 1
    return list(struct.unpack_from('>h2xIII', data, hits[0] + 8))


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('captures', type=Path, nargs='+')
p.add_argument('--centering',action='store_true',help='Verify native centering scalar adjustment using PDKEY probes')
a = p.parse_args()
for root in a.captures:
    remainder = initial_remainders(root / 'code.bin')
    log=(root/'swaps-gdb.txt').read_text()
    key_scalars=iter([list(map(int,v.split())) for v in re.findall(r'^PDKEY_EVENT -?\d+ 0xcd2c (.+)$',log,re.M)])
    start = scalar = vector = None
    pending = None
    completed = carried_scalar = carried_vector = checks = adjustments = 0
    for line in log.splitlines():
        parts = line.split()
        if not parts or parts[0] not in ('PDMOVE_EVENT', 'PDR20_EVENT'):
            continue
        kind, field, offset = parts[:3]
        off = int(offset, 16)
        v = list(map(int, parts[3:]))
        if kind == 'PDR20_EVENT':
            assert pending == (field, offset), 'Missing or misordered remainder probe'
            assert [signed16(v[0]), *v[1:]] == remainder, (root.name, field, off, v, remainder)
            pending = None
            checks += 1
            continue
        assert pending is None, 'Missing remainder observation'
        assert len(v) == 14
        if off == 0xccee:
            assert start is None
            start = v
        elif off == 0xcd2c:
            assert start is not None and scalar is None
            assert v[0] == 4, 'Expected a 20-ms step'
            carried_scalar += bool(remainder[0])
            numerator = signed16(v[1]) * v[0] + remainder[0]
            quotient = (abs(numerator) // 24) * (-1 if numerator < 0 else 1)
            remainder[0] = numerator - quotient * 24
            adjusted=quotient
            if a.centering:
                key=next(key_scalars)
                assert len(key)==15
                modifier,on,strength,mode,disabled=key[4],*key[11:15]
                if on and not disabled:
                    product=signed16(quotient)*signed16(strength)
                    denominator=540 if mode else 360
                    reduction=(abs(product)//denominator)*(-1 if product<0 else 1)
                    if not mode:reduction=signed16(reduction)>>1
                    adjusted=signed16(quotient-reduction)
                    if modifier&1:adjusted >>= 1
            adjustments += adjusted != quotient
            assert signed16(v[2]) == adjusted, ('Scalar carry/centering mismatch',field,v[2],adjusted)
            scalar = v
            pending = (field, offset)
        elif off == 0xcd3a:
            assert scalar is not None and vector is None
            expected = []
            for axis, reg in enumerate((3, 4, 5), 1):
                carried_vector += bool(remainder[axis])
                product = signed16(scalar[reg]) * signed16(scalar[2]) + remainder[axis]
                expected.append((product >> 12) & 65535)
                remainder[axis] = product & 4095
            assert v[3:6] == expected, ('Vector carry mismatch', field, v[3:6], expected)
            vector = v
            pending = (field, offset)
        elif off == 0xcde2:
            assert start is not None and scalar is not None and vector is not None
            assert v[6:9] == start[9:12], 'Previous position was not preserved'
            completed += 1
            start = scalar = vector = None
    assert pending is None
    if a.centering:assert next(key_scalars,None) is None, 'Unmatched scalar input-state probes'
    assert completed >= 50 and checks >= 2 * completed
    if a.centering:
        assert adjustments>=20, 'Capture did not exercise centering scalar adjustments'
    else:
        assert carried_scalar and carried_vector, 'Capture did not exercise both fractional carries'
    assert initial_remainders(root / 'final-code.bin') == remainder, 'Unobserved remainder mutation'
    print(f'{root.name}: {completed} complete movements, {checks} remainder observations; '
          f'{carried_scalar} scalar and {carried_vector} axis carries verified; {adjustments} centering adjustments')
