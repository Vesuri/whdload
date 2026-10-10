#!/usr/bin/env python3
"""Compare original/development input-fixture captures with CUSTOM1 off.

Checks Copylock's D2 lifetime, relocated game text, main state and planar bitmaps.
Explicitly accounts for allocation, elapsed-time/RNG and displayed clock differences;
this is not a claim of cycle-identical OS implementations or exhaustive gameplay coverage.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
import adf

PROBES = (0x8962, 0x173b2, 0x173b6, 0x16c4c, 0x16c4e, 0x11d70)
PATCHES = (0x843c, 0x13772, 0x1377c, 0x12f6a, 0x130a4, 0x13c50, 0x13cde)
STATE = 0xa6e
STATE_SIZE = 0xf96 - STATE
# Named main-state pointers; only equal game-relative values may be normalized.
POINTERS = (0x1e, 0x22, 0x26, 0x2a, 0x2e, 0x32, 0x36, 0x3a, 0x3e,
            0x42, 0x46, 0x4a, 0x4e, 0x56, 0xee, 0x2aa, 0x3b2, 0x3b6,
            0x3ba, 0x3be, 0x3c6, 0x3ca, 0x3ce, 0x3d2, 0x41e, 0x4aa,
            0x4b0, 0x512)
CLOCKS = (0x206, 0x218, 0x47e)


def u32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def registers(path):
    return {k: int(v, 16) for k, v in
            re.findall(r'^(\w+)\s+0x([a-f0-9]+)', path.read_text(), re.M)}


def executable(disk):
    image = disk.read_bytes()
    exe = adf.read(image, next(h for name, h, _ in adf.walk(image) if name.lower() == 'pd'))
    assert u32(exe, 24) == 0x3e9
    size = u32(exe, 28)*4
    assert u32(exe, 32+size) == 0x3ec
    offsets, pos = [], 36+size
    while (count := u32(exe, pos)):
        assert u32(exe, pos+4) == 0
        offsets.extend(struct.unpack_from(f'>{count}I', exe, pos+8))
        pos += 8+4*count
    return size, offsets


def compare(left, right, disk):
    roots = (left, right)
    configs = [json.loads((p/'configuration.json').read_text()) for p in roots]
    for key in ('CPU', 'AMIGA_MODEL', 'CHIP_KB', 'FAST_KB', 'EXTRA_ARGS', 'WHD_ARGS',
                'kickstart_sha256', 'emulator_sha256', 'FIELDS', 'ANCHOR', 'PROBE_OFFSETS'):
        assert configs[0][key] == configs[1][key], f'Configuration mismatch: {key}'
    assert 'CUSTOM1=0' in configs[0]['WHD_ARGS'].split()
    assert int(configs[0]['ANCHOR'], 0) == 0x14764 and int(configs[0]['FIELDS']) == 500
    for root, config in zip(roots, configs):
        assert hashlib.sha256((root/'slave.slave').read_bytes()).hexdigest() == config['slave_sha256']
    bases = [int((p/'game-base.txt').read_text(), 0) for p in roots]
    size, relocations = executable(disk)
    result = {'cpu': configs[0]['CPU'], 'slave_sha256': [c['slave_sha256'] for c in configs],
              'copylock_and_d2': {}, 'checkpoints': {}}
    for off in PROBES:
        regs = [registers(p/f'probe-{off:#x}-registers.txt') for p in roots]
        assert all(r['pc'] == b+off for r, b in zip(regs, bases)), f'Wrong probe {off:#x}'
        result['copylock_and_d2'][hex(off)] = [r['d2'] for r in regs]
        if off == 0x8962:
            assert all(r['d0'] == 0x766cc95c for r in regs), 'Copylock key differs'
        if off in (0x173b6, 0x16c4c, 0x16c4e, 0x11d70):
            assert regs[0]['d2'] == regs[1]['d2'], f'D2 did not converge at {off:#x}'
        if off == 0x16c4e:
            assert all(r['d2'] == 4 for r in regs)

    for name, filename in (('copylock_return', 'probe-0x8962-chip.bin'),
                           ('name_entered', 'probe-0x11d70-chip.bin'),
                           ('pit_departure', 'chip.bin')):
        memory = [(p/filename).read_bytes() for p in roots]
        code = [bytearray(m[b:b+size]) for m, b in zip(memory, bases)]
        for data, base in zip(code, bases):
            assert data[0x173b2:0x173b6] == bytes.fromhex('342e0466')
            assert data[0x16c4c:0x16c4e] == bytes.fromhex('7404')
            for off in PATCHES:
                assert data[off:off+2] == (b'\x4e\xf9' if off == 0x843c else b'\x4e\xb9')
            for off in relocations:
                struct.pack_into('>I', data, off, (u32(data, off)-base) & 0xffffffff)
            for off in PATCHES:
                data[off:off+6] = bytes(6)
        assert code[0][0x4fc0:] == code[1][0x4fc0:], f'Game text differs at {name}'
        entry = {'game_text_equal_after_relocation_and_named_patches': True}
        entry['saved_argument_lengths'] = [u32(m, b+0x4948) for m, b in zip(memory, bases)]
        assert entry['saved_argument_lengths'][1] == 0, 'Development launch arguments are invalid'
        assert all(u32(m, b+0x4f74) == 0 for m, b in zip(memory, bases)), 'Command-line behavior differs'
        result['checkpoints'][name] = entry
        if name == 'copylock_return':
            continue
        state = [bytearray(m[b+STATE:b+STATE+STATE_SIZE]) for m, b in zip(memory, bases)]
        adjusted = []
        for off in POINTERS:
            values = [u32(s, off) for s in state]
            if values[0] == values[1]:
                continue
            assert all(b <= v < len(m) for v, b, m in zip(values, bases, memory))
            assert values[0]-bases[0] == values[1]-bases[1], f'Pointer mismatch {off:#x}'
            for s, v, b in zip(state, values, bases):
                struct.pack_into('>I', s, off, v-b)
            adjusted.append(hex(off))
        entry['relocated_state_pointers'] = adjusted
        entry['elapsed_time_fields'] = {hex(off): [u32(s, off) for s in state] for off in CLOCKS}
        entry['last_frame_delta'] = [int.from_bytes(s[0x21c:0x21e], 'big') for s in state]
        entry['random_seed'] = [int.from_bytes(s[0x62:0x64], 'big') for s in state]
        for s, m, b in zip(state, memory, bases):
            assert u32(s, 0x14) == sum(m[b+0x8958:b+0x15596]), 'Invalid game checksum'
            assert s[0x18:0x1a] == b'\0\0', 'Protection failure flag set'
            assert u32(m, b+0x4fa2) == u32(m, b+0x4faa) == 0x766cc95c
            s[0x14:0x18] = bytes(4)
            for off in CLOCKS:
                s[off:off+4] = bytes(4)
            s[0x62:0x64] = bytes(2)
            s[0x21c:0x21e] = bytes(2)
        different = [hex(i) for i in range(STATE_SIZE) if state[0][i] != state[1][i]]
        assert not different, f'Unexplained main-state difference at {name}: {different}'
        entry['remaining_main_state_equal'] = True
        bitmaps = []
        for off in (0x4696, 0x46be):
            images = []
            for m, b in zip(memory, bases):
                row, rows, flags, depth = struct.unpack_from('>HHBB', m, b+off)
                assert (row, rows, depth) == (40, 200, 4)
                planes = struct.unpack_from('>4I', m, b+off+8)
                assert all(0 < p and p+8000 <= len(m) for p in planes)
                images.append(b''.join(m[p:p+8000] for p in planes))
            diffs = [i for i, (a, b) in enumerate(zip(*images)) if a != b]
            if name == 'name_entered':
                assert not diffs, 'Name-entry bitmap differs'
            else:
                # ET: mm:ss uses plane 1, rows 5..11, five glyphs at x=144..183.
                # Retain the raw differences rather than declaring full pixel equality.
                assert all(i//8000 == 1 and 5 <= i%8000//40 <= 11 and
                           18 <= i%40 <= 22 for i in diffs), 'Non-clock pit pixels differ'
            bitmaps.append({'descriptor': hex(off), 'different_bytes': len(diffs),
                            'differences_confined_to_elapsed_time_text': bool(diffs)})
        entry['bitmaps'] = bitmaps
    result['frames'] = []
    for root in roots:
        text = (root/'frames.txt').read_text()
        fields = re.search(r'per field: (\d+)', text)[1]
        assert len(fields) == 500 and sum(map(int, fields)) > 1
        result['frames'].append({'first_driving_presentation_field': next(i for i, n in enumerate(fields) if n != '0'),
                                 'presentations': sum(map(int, fields)), 'summary': text.splitlines()[-1]})
    result['status'] = 'passed_with_explicit_allocation_and_timing_differences'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('development', type=Path)
    parser.add_argument('--disk', type=Path, default=Path('tmp/game/Powerdrome/Disk.1'))
    args = parser.parse_args()
    print(json.dumps(compare(args.original, args.development, args.disk), indent=2))
