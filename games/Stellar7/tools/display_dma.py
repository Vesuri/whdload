#!/usr/bin/env python3
"""Compare lossless display fetches in settled FRAME_TEST captures.

Scope: the observed 320x200, four-plane, non-scrolling OCS-compatible display
with no hardware sprites, conflicts or CPU display writes. Unsupported modes
fail closed. Addresses are not pixels: compare fetched words, beam positions,
and effective palette/control state instead of allocation-dependent pointers.
"""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path
import barto
from frame_state import inspect as inspect_frame

CONTROLS = (0x8e, 0x90, 0x92, 0x94, 0x100, 0x102, 0x104, 0x108, 0x10a)
PLANES = (0x110, 0x112, 0x114, 0x116)


def field_state(field):
    assert field.dma_size == 58 and len(field.dma) == 58*227*313, 'unknown DMA layout'
    assert len(field.custom) == 520, 'unknown full save_custom layout'
    # save_custom begins with a four-byte chipset mask, followed by register
    # words in hardware-address order, then a final four-byte refresh pointer.
    word = lambda reg: struct.unpack_from('>H', field.custom, 4+reg)[0]
    assert word(0x106) == 0xc00 and word(0x10c) == 0x11 and word(0x1fc) == 0, 'unsupported AGA mode'
    assert not word(0x1e4) & 0x8000, 'explicit DIWHIGH needs separate modeling'
    chipset = struct.unpack_from('>I', field.custom)[0]
    assert chipset in (0, 7), 'unvalidated chipset configuration'
    if chipset == 7:
        assert len(field.aga_colors) == 1024, 'AGA palette snapshot missing'
        for i in range(16):
            v = word(0x180+2*i)
            rgb = ((v >> 8 & 15)*17 << 16) | ((v >> 4 & 15)*17 << 8) | (v & 15)*17
            assert struct.unpack_from('>I', field.aga_colors, 4*i)[0] == rgb, 'non-OCS-compatible AGA palette'
    assert all(word(0x144+8*i) == word(0x146+8*i) == 0 for i in range(8)), 'live sprite data'
    palette = {}
    controls = {}
    rows = collections.defaultdict(list)
    color_writes = collections.defaultdict(list)
    control_writes = []
    for off in range(0, len(field.dma), 58):
        reg, value, size, address = struct.unpack_from('<HQHI', field.dma, off)
        kind = struct.unpack_from('<h', field.dma, off+29)[0]
        conflict = struct.unpack_from('<H', field.dma, off+36)[0]
        assert conflict == 0xffff, 'unmodeled conflicting DMA transaction'
        y, x = divmod(off//58, 227)
        assert kind != 7, 'hardware sprites require separate modeling'
        if kind == 2 and reg < 0x200:
            assert reg not in CONTROLS and not 0xe0 <= reg <= 0x1fe, 'CPU display access'
        if kind == 3:
            if reg in CONTROLS:
                expected = {0x8e: 0x581, 0x90: 0x40c1, 0x92: 0x38, 0x94: 0xd0,
                            0x102: 0, 0x104: 0x24, 0x108: 0, 0x10a: 0}
                assert value in ((0x200, 0x4200) if reg == 0x100 else (expected[reg],)), 'unsupported display control'
                controls[reg] = value
                control_writes.append((y, x, reg, value))
            elif reg in (0x106, 0x10c, 0x1e4, 0x1fc) or 0x110 <= reg < 0x120 or 0x140 <= reg < 0x180:
                raise AssertionError('unmodeled display-mode/sprite write')
            elif 0x180 <= reg < 0x1c0:
                assert value <= 0xfff, 'non-12-bit color'
                palette[(reg-0x180)//2] = value
                color_writes[y].append((x, (reg-0x180)//2, value))
        if kind == 6:
            assert reg in PLANES and size == 2 and value <= 65535, 'unsupported bitplane fetch'
            assert set(CONTROLS) <= controls.keys(), 'display setup missing before fetch'
            assert set(range(16)) <= palette.keys(), 'palette setup missing before fetch'
            assert controls[0x100] == 0x4200 and controls[0x102] == 0, 'unsupported pixel mode'
            rows[y].append((x, reg, value, tuple(palette[i] for i in range(16)),
                            tuple(controls[i] for i in CONTROLS)))
    assert sorted(rows) == list(range(44, 244)), 'unexpected display lines'
    digest = hashlib.sha256()
    word_digest = hashlib.sha256()
    assert word(0x100) == 0x200, 'display not blank at field start'
    assert [(y, v) for y, x, r, v in control_writes if r == 0x100] == [(42, 0x200), (44, 0x4200), (244, 0x200)], 'unexpected display enable window'
    digest.update(struct.pack('>25H', *(word(r) for r in CONTROLS), *(word(0x180+2*i) for i in range(16))))
    for entry in control_writes:
        digest.update(struct.pack('>4H', *entry))
    # Keep every background-color write and every visible palette write at
    # its exact beam position. Nonzero colors changed before a row's first
    # fetch cannot affect output there: no sprites, and no pixels fetched yet.
    # Their effective values are still compared at every following fetch.
    for y, writes in sorted(color_writes.items()):
        first = rows[y][0][0] if y in rows else 227
        for x, color, value in writes:
            if color == 0 or x >= first:
                digest.update(struct.pack('>4H', y, x, color, value))
    for y, fetches in sorted(rows.items()):
        assert collections.Counter(r[1] for r in fetches) == {r: 20 for r in PLANES}, 'incomplete scanline'
        first = fetches[0][0]
        assert 2*first < (fetches[0][4][0] & 0xff), 'prefetch must precede horizontal display start'
        assert len({r[4] for r in fetches}) == 1, 'mid-line display-control effect'
        for x, reg, value, colors, settings in fetches:
            word_digest.update(struct.pack('>4H', y, x, reg, value))
            digest.update(struct.pack('>29H', y, x, reg, value, *colors, *settings))
    return dict(lines=200, words=16000, bitplane_sha256=word_digest.hexdigest(),
                effective_display_sha256=digest.hexdigest())


def inspect(folder, listing):
    folder = Path(folder)
    frame, _ = inspect_frame(folder, listing)
    trace = barto.load(folder/'trace.bin')
    settled = [f for f in trace.fields if f.index >= frame['first_hold_field']+2]
    states = [field_state(f) for f in settled]
    assert all(s == states[0] for s in states), 'display DMA changes during held frame'
    return dict(**states[0], settled_fields=len(settled),
                scope='Lossless fetched bitplane words and effective palette/control state for the guarded display mode; no claim about unused host screenshot-buffer edges.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--listing', required=True, type=Path)
    a = p.parse_args()
    result = inspect(a.capture, a.listing)
    (a.capture/'display-dma.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
