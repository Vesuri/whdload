#!/usr/bin/env python3
"""A4 evidence: decode pinned pose paths and check retained A3 camera snapshots.

Usage: python3 tools/state_map.py tmp/a3 tmp/a4/state-map.json
Requires Capstone 5. No emulator or shared-tool changes; all derived output is scratch.
This validates the documented source/copy relationships, not extrapolation or every UI
view. TV/front-chase branches are statically mapped; dynamic coverage is reported.
"""
import argparse
import gzip
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
from check_disabled import relocated_original
from slave_inputs import ROOT, verify
from state_diff import digest, scratch

# Straight-line ranges selected at instruction boundaries; no data is disassembled.
PATHS = {
    'car walk': (0, 0x2ac22, 0x2ac4a),
    'pose dispatch and track projection': (0, 0x26206, 0x26326),
    'speed and motion heading': (0, 0x25f4e, 0x25fca),
    'track coordinates and fraction': (0, 0x2b95a, 0x2ba42),
    'height and pitch': (0, 0x2ba96, 0x2bae4),
    'lap position': (0, 0x2bae4, 0x2bb40),
    'camera publication': (0, 0x33ea6, 0x340e8),
    'camera spring': (0, 0x3676a, 0x367a4),
    'external camera dispatch': (0, 0x397e4, 0x39cf2),
    'view selection': (0, 0x3c292, 0x3c55c),
    'car draw inputs': (2, 0x29a20, 0x29b2c),
    'object transform': (2, 0x28652, 0x2874a),
    'wheel steering images': (2, 0x28be0, 0x28d40),
    'road camera transform': (2, 0x2327e, 0x232d0),
    'mirror/secondary track pass': (2, 0x2a450, 0x2a62e),
}


def static_paths():
    bases = [0x100000, 0x200000, 0x300000, 0x400000]
    hunks = relocated_original(bases)
    decoder = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    result = {}
    for name, (h, start, end) in PATHS.items():
        rows = []
        pc = bases[h] + start
        for ins in decoder.disasm(hunks[h][start:end], pc):
            if ins.address != pc or ins.mnemonic == 'dc.w':
                raise ValueError(f'undecoded instruction in {name} at {pc:x}')
            rows.append(dict(pc=f'h{h}+{pc-bases[h]:05x}',
                             instruction=ins.mnemonic + ' ' + ins.op_str))
            pc += ins.size
        if pc != bases[h] + end:
            raise ValueError(f'incomplete path {name}: {pc-bases[h]:x} != {end:x}')
        result[name] = rows
    return result


def check_capture(directory):
    meta = json.loads((directory / 'meta.json').read_text())
    pins = json.loads((ROOT / 'manifest/game-inputs.json').read_text())
    if meta['status'] != 'CAPTURED' or meta['frames'] != 50 or meta['game_inputs'] != pins:
        raise ValueError(f'unaccepted capture metadata: {directory}')
    sizes = meta['hunk_sizes']
    if sizes != [0x44a54, 0x2a940, 0x41c70, 0x14f84]:
        raise ValueError('unexpected hunk sizes')
    events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
    site = 0x3cce2 if meta['mode'] == 'replay' else 0x3c9b4
    selected = [e for e in events if e['site'] == site and e['edge'] == 'after']
    if sorted(e['frame'] for e in selected) != list(range(50)):
        raise ValueError('missing/duplicate camera-return frames')
    rows = []
    for event in selected:
        path = scratch(directory / event['file'])
        data = gzip.decompress(path.read_bytes())
        if len(data) != sum(sizes) or digest(data) != event['sha256']:
            raise ValueError(f'corrupt snapshot: {path}')
        h0, h1 = data[:sizes[0]], data[sizes[0]:sum(sizes[:2])]
        u16 = lambda b, o: struct.unpack_from('>H', b, o)[0]
        u32 = lambda b, o: struct.unpack_from('>I', b, o)[0]
        source = u32(h1, 0x234) - meta['hunk_bases'][1]
        target = u32(h1, 0x238) - meta['hunk_bases'][1]
        car = lambda o: 0x5d6 <= o < 0x1956 and (o - 0x5d6) % 0xc0 == 0
        view = h1[0x23c]
        if not car(target) or source != (target if view == 0 else 0x256):
            raise ValueError('camera-source selection disagrees with map')
        # Direct copies made by 33ECE..33EEC, independently of pose representation.
        for car_off, camera_off in [(0, 0x3a7f8), (0x1a, 0x3a80c),
                                    (0xa, 0x3a80a), (0x26, 0x3a81c)]:
            if u16(h1, source + car_off) != u16(h0, camera_off):
                raise ValueError(f'camera copy mismatch: {directory.name} {event["frame"]}')
        explicit = bool(h1[source + 0x7e] & 1)
        if explicit:
            for car_off, camera_off in [(0x28, 0x3a802), (0x2c, 0x3a806)]:
                if u32(h1, source + car_off) != u32(h0, camera_off):
                    raise ValueError('explicit world coordinate mismatch')
        for full, reduced, integer in [(0x3a802, 0x3a810, 0x3a7fc),
                                       (0x3a806, 0x3a818, 0x3a800)]:
            value = struct.unpack_from('>i', h0, full)[0]
            if u32(h0, reduced) != (value >> 8) & 0xffffffff:
                raise ValueError('camera fixed-point reduction mismatch')
            if u16(h0, integer) != (value >> 11) & 0xffff:
                raise ValueError('camera coarse-coordinate mismatch')
        rows.append(dict(frame=event['frame'], snapshot_sha256=event['sha256'],
                         view=f'{view:02x}', source=f'h1+{source:05x}',
                         target=f'h1+{target:05x}', explicit_pose=explicit))
    return dict(status='PASS', mode=meta['mode'], frames=len(rows),
                capture_meta_sha256=digest((directory/'meta.json').read_bytes()),
                events_sha256=digest((directory/'events.jsonl').read_bytes()),
                emulator_sha256=meta['emulator_sha256'], slave_sha256=meta['slave_sha256'],
                samples=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    out = scratch(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('{"status":"INCOMPLETE"}\n')
    verify()
    paths = static_paths()
    captures = {name: check_capture(scratch(args.captures / name))
                for name in ('green', 'tow', 'follow', 'qualifying', 'replay')}
    result = dict(status='PASS', game_inputs=json.loads((ROOT/'manifest/game-inputs.json').read_text()),
                  scope='Static pose paths and 250 retained A3 camera-return snapshots; not all-view UI acceptance',
                  static_paths=paths, captures=captures)
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'PASS: {len(paths)} static paths; 250 camera-return snapshots; {out}')


if __name__ == '__main__':
    main()
