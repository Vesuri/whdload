#!/usr/bin/env python3
"""Recover/validate ray-table geometry using local game data; never emit game bytes.

Each row starts with an octant, then (unsigned Q16 minor/major slope,
rounded reciprocal major-axis projection) per column. A zero word switches
to the preceding octant. Bytes after the last column are not consumed.
"""
import argparse
import math
import struct
from pathlib import Path

VIEWS = ((192, 180, 'mt0.dat'), (112, 105, 'mt2.dat'), (80, 75, 'mt3.dat'))
Q = 1 << 22


def octant(x, y):
    if x >= 0:
        return (0 if x > y else 1) if y >= 0 else (7 if x > -y else 6)
    return (2 if y > -x else 3) if y >= 0 else (4 if -x > -y else 5)


def row(width, focal, heading, fixed=False):
    # This adjacent double reproduces the legacy cardinal rounding, including
    # its asymmetric truncation at 90 degrees. It is an empirical match, not
    # a claim about the original offline generator's implementation.
    angle = heading * math.nextafter(math.pi, math.inf) / 180
    if fixed:
        sine = round(math.sin(math.radians(heading)) * Q)
        cosine = round(math.cos(math.radians(heading)) * Q)
        x = 2*focal*cosine - (width-1)*sine
        y = 2*focal*sine + (width-1)*cosine
    result, previous = [], None
    for column in range(width):
        if not fixed:
            lateral = ((width-1)/2-column)/focal
            x = math.cos(angle)-lateral*math.sin(angle)
            y = math.sin(angle)+lateral*math.cos(angle)
        region = octant(x, y)
        if previous is None:
            result.append(region)
        elif region != previous:
            assert region == (previous-1) % 8
            result.append(0)
        previous = region
        major, minor = max(abs(x), abs(y)), min(abs(x), abs(y))
        if fixed:
            slope = (minor << 16)//major
            scale = ((1 << 39) + major//2)//major
        else:
            slope = int(minor/major*65536)
            scale = int((65536/focal)/major+0.5)
        # Zero is a control marker; one overflows the native 65536/DIVU.
        slope = max(2, slope)
        assert slope < 65536 and 0 < scale < 65536
        result.extend((slope, scale))
        if fixed:
            x += 2*sine
            y -= 2*cosine
    assert len(result) <= 2*(width+8)
    return result


def decode(words, width):
    region, at, columns = words[0], 1, []
    assert 0 <= region < 8
    while len(columns) < width:
        slope = words[at]
        at += 1
        if slope == 0:
            region = (region-1) % 8
            continue
        scale = words[at]
        at += 1
        assert scale
        columns.append((region, slope, scale))
    return columns, at


def validate(data):
    legacy_columns = new_columns = 0
    max_slope = max_scale = 0
    for width, focal, filename in VIEWS:
        raw = (data/filename).read_bytes()
        stride = 4*(width+8)
        assert len(raw) == 36*stride
        for heading in range(180):
            expected = row(width, focal, heading)
            ref, used = decode(expected, width)
            if heading % 5 == 0:
                original = struct.unpack_from('>'+str(stride//2)+'H', raw, heading//5*stride)
                assert list(original[:used]) == expected, (filename, heading)
                legacy_columns += width
            else:
                candidate, _ = decode(row(width, focal, heading, fixed=True), width)
                for column, (a, b) in enumerate(zip(ref, candidate)):
                    assert a[0] == b[0], (filename, heading, column, 'octant')
                    ds, dp = abs(a[1]-b[1]), abs(a[2]-b[2])
                    assert ds <= 1 and dp <= 1, (filename, heading, column, a, b)
                    max_slope, max_scale = max(max_slope, ds), max(max_scale, dp)
                new_columns += width
        print(f'{filename}: all 36 legacy rows exact over consumed entries; 144 finer rows checked')
    print(f'{legacy_columns} legacy and {new_columns} intermediate columns; '
          f'fixed-point max error slope={max_slope}/65536, projection={max_scale}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('tmp/game/LegendsOfValour/data'))
    args = parser.parse_args()
    validate(args.data)
