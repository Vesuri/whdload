#!/usr/bin/env python3
"""Validate a FRAME_TEST capture and extract its settled displayed image.

The fixture draws a specified completed simulation tick then holds gameplay.
Require the exact retained build, one presentation, and stable pixels after
render completion; this is an image-equivalence check, not a performance run.
"""
import argparse
import hashlib
import io
import json
import re
import struct
from pathlib import Path
from PIL import Image
import barto
from stellar7_report import locate


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    source = listing.read_text(encoding='latin1')
    section = source.split('Source: "frame60_test.s"')[1]
    hold_offset = int(re.search(r'^00:([0-9A-F]+)\s+60FE\s+\d+: \.hold:', section, re.M)[1], 16)
    render_offset = int(re.search(r'^s60_render\s+00:([0-9A-F]+)', source, re.M)[1], 16)
    size = struct.unpack_from('>I', binary, 28)[0]*4
    body = binary[32:32+size]
    assert body[hold_offset:hold_offset+2] == bytes.fromhex('60fe')
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    address = locate((folder/'code.bin').read_bytes(), body, meta['base'], header=32)
    assert address is not None
    trace = barto.load(folder/'trace.bin')
    hold_fields, presentations, renders = [], [], []
    for field in trace.fields:
        held = False
        for pc, cost, regs in trace.instructions(field):
            if pc == address+hold_offset:
                held = True
            elif pc == address+render_offset:
                renders.append(field.index)
            elif pc == meta['code']+0x6a0a:
                presentations.append(field.index)
        if held:
            hold_fields.append(field.index)
    assert hold_fields, 'render never reached the hold loop'
    # Profiling starts at the next field after the tick boundary; the
    # render entry can precede that field. Presentation and hold must be seen.
    assert len(renders) <= 1 and len(presentations) == 1, (renders, presentations)
    # Exclude the transition field and the following scan. Compare every
    # remaining displayed field, not just a chosen pair of matching pictures.
    settled = [f for f in trace.fields if f.index >= hold_fields[0]+2]
    assert len(settled) >= 20, 'insufficient settled display coverage'
    hashes = []
    for field in settled:
        im = Image.open(io.BytesIO(field.shot)).convert('RGBA')
        hashes.append(hashlib.sha256(im.tobytes()).hexdigest())
    assert len(set(hashes)) == 1, 'display pixels change after gameplay is held'
    return dict(render_fields=renders, presentation_fields=presentations,
                first_hold_field=hold_fields[0], settled_fields=len(settled),
                image_size=list(im.size), source_image_format=Image.open(io.BytesIO(settled[-1].shot)).format,
                rgba_sha256=hashes[0]), settled[-1].shot


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result, png = inspect(args.capture, args.listing)
    # Multi-field Barto captures use JPEG; store a correctly named PNG of
    # those decoded pixels, without pretending this recovers lost detail.
    Image.open(io.BytesIO(png)).convert('RGBA').save(args.capture/'settled.png')
    (args.capture/'frame-validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
