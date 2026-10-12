#!/usr/bin/env python3
"""Check visible weather colour at three logical phases of one directed fade.

Prepared Copper palettes are exact. Barto's screen image is JPEG, so visible
flat weather regions are checked within a derived DC-quantization bound;
this is not an exact whole-frame pixel comparison. Renderer twins cover the latter
before scanout. Reject phases ambiguous with another palette entry.
"""
import argparse
import json
import math
import struct
from pathlib import Path

from PIL import Image
import _amigaxdev
from amigaxdev import barto
from check_weather_copper import check as check_copper
from weather_fade_state import snapshot as fade_snapshot
from weather_palette_state import interpolate, snapshot as palette_snapshot


def rgb(word):
    return tuple(((word >> shift) & 15) * 17 for shift in (8, 4, 0))


def jpeg_bound(image):
    assert image.format == 'JPEG', 'Expected the profiler JPEG image'
    tables = image.quantization
    assert 0 in tables and 1 in tables, 'Missing luminance/chrominance quantizers'
    # A constant 8x8 block has only DC: quantization error <= Qdc/16 per
    # component after inverse DCT. Two extra levels cover integer conversions.
    y, c = tables[0][0] / 16, tables[1][0] / 16
    return tuple(math.ceil(y + coefficient*c + 2) for coefficient in (1.402, 1.059, 1.772))


def check_phase(root):
    meta = json.loads((root/'phase.json').read_text())
    before, after = fade_snapshot(root), fade_snapshot(root, True)
    assert meta['before'] == before and meta['after'] == after
    assert before['negative'] == after['negative'] == 0
    assert before['pending'] == after['pending'] == 0
    assert 1 <= before['published'] <= 14
    assert all(before[key] == after[key] for key in ('published', 'positive', 'transition'))
    phase = 15-before['published']
    assert meta['phase'] == phase
    p, q = palette_snapshot(root), palette_snapshot(root, True)
    assert p == q, 'Palette changed during the screenshot fields'
    expected_word = interpolate(p['source'], p['target'], phase)
    assert p['current'][5] == p['saved'][5] == expected_word, 'Wrong logical fade colour'
    check_copper(root)
    check_copper(root, True)
    expected = rgb(expected_word)
    trace = barto.load(root/'screen.bin')
    assert len(trace.fields) == 2, 'Need two complete profiler fields'
    assert trace.fields[-1].shot == (root/'screen.jpg').read_bytes(), 'Image differs from its profiler field'
    with Image.open(root/'screen.jpg') as image:
        bounds = jpeg_bound(image)
        visible = image.convert('RGB')
    # A unique palette entry identifies weather, independent of how much track
    # wall fills the view. Also require a flat source region in both bitmaps.
    for index, word in enumerate(p['current']):
        if index != 5:
            assert any(abs(a-b) > 2*bound for a,b,bound in zip(expected,rgb(word),bounds)), 'Ambiguous weather colour'
    chip = (root/'chip.bin').read_bytes()
    game = int((root/'game-base.txt').read_text(), 0)
    source_regions = []
    for bitmap in (0x4696, 0x46be):
        stride, height = struct.unpack_from('>HH', chip, game+bitmap)
        assert stride == 40 and height == 200, 'Unsupported scene dimensions'
        planes = struct.unpack_from('>4I', chip, game+bitmap+8)
        rows = []
        for y in range(height):
            rows.append([sum(((chip[plane+y*stride+x//8] >> (7-x%8)) & 1) << n
                             for n,plane in enumerate(planes)) for x in range(stride*8)])
        flat = [(x,y) for y in range(height-7) for x in range(stride*8-7)
                if all(rows[yy][xx] == 5 for yy in range(y,y+8) for xx in range(x,x+8))]
        assert flat, 'No flat weather region in scene bitmap'
        source_regions.append(len(flat))
    # Whole 16x16 JPEG blocks avoid treating isolated edge/chroma-blend pixels
    # as a visible flat colour. Retain the independently derived DC bound.
    regions = []
    for y in range(0,visible.height-15,16):
        for x in range(0,visible.width-15,16):
            extrema = visible.crop((x,y,x+16,y+16)).getextrema()
            if all(lo >= value-bound and hi <= value+bound
                   for (lo,hi),value,bound in zip(extrema,expected,bounds)):
                regions.append((x,y))
    assert regions, ('No flat visible weather block matches Copper', expected, bounds)
    result = dict(phase=phase, copper_rgb4=f'{expected_word:03x}', expected_rgb=expected,
                  source_flat_regions=source_regions, visible_blocks=regions,
                  jpeg_dc_bounds=bounds)
    print(json.dumps(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    roots = sorted(args.capture.glob('phase-*'), key=lambda p:int(p.name.split('-')[1]))
    assert len(roots) == 3, 'Need exactly three logical-phase screenshots'
    configs = [json.loads((root/'configuration.json').read_text()) for root in roots]
    assert all(config == configs[0] for config in configs), 'Capture configurations differ'
    fades = [fade_snapshot(root) for root in roots]
    assert len({fade['start'] for fade in fades}) == 1, 'Different logical fade episodes'
    assert all(a['positive'] < b['positive'] for a,b in zip(fades,fades[1:])), 'Fade checkpoints are out of order'
    results = [check_phase(root) for root in roots]
    assert len({result['phase'] for result in results}) == 3
    assert len({result['copper_rgb4'] for result in results}) == 3
    print('Three visible weather colours match their exact logical/Copper phases within JPEG DC bounds.')


if __name__ == '__main__':
    main()
