#!/usr/bin/env python3
"""Audit compiled SIM60 patch boundaries and potential direct interior entries.

Decodes the original instructions at every merged patch range. Scans every
aligned native word (including data/operands) conservatively for direct branches,
PC-relative JSR/JMP and relocated absolute JSR/JMP, plus all relocated code
pointers. Computed indirect destinations and replacement semantics are outside
this static check and need separate validation.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import capstone
from check_disabled import hunks, patch_size
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.patchlist import decode, slave_code
from stellar7_report import GAME, locate


def compiled_patches(listing):
    listing = Path(listing)
    listing_text = listing.read_text(encoding='latin1')
    symbols = {name: int(offset, 16) for name, offset in re.findall(
        r'^(\w+)\s+00:([0-9A-F]+)', listing_text, re.M)}
    slave = slave_code(listing.with_suffix('.slave'))
    emitted = re.findall(r'^00:([0-9A-F]+)\s+([0-9A-F]+)\s', listing_text, re.M)
    assert emitted, 'listing has no emitted bytes'
    for offset, encoded in emitted:
        start = int(offset, 16)
        expected = bytes.fromhex(encoded)
        assert slave[start:start+len(expected)] == expected, f'listing byte mismatch at {start:#x}'
    result = []
    for name, start in symbols.items():
        if not (name.startswith('s60_') and name.endswith('_patches')):
            continue
        for offset, command, argument in decode(slave, start):
            if command != 'END':
                result.append(dict(start=offset, end=offset+patch_size(command, argument),
                                   command=command, argument=argument, patch_list=name))
    result.sort(key=lambda patch: patch['start'])
    assert result, 'no SIM60 patch lists'
    for a, b in zip(result, result[1:]):
        assert a['end'] <= b['start'], f'overlapping patches: {a}, {b}'
    return result


def audit(listing, original=None, patches=None):
    original = hunks(GAME) if original is None else original
    patches = compiled_patches(listing) if patches is None else patches
    code, relocations = original[0]
    groups = []
    for patch in patches:
        assert patch['start'] % 2 == 0
        assert 0 <= patch['start'] < patch['end'] <= len(code)
        if groups and patch['start'] == groups[-1][-1]['end']:
            groups[-1].append(patch)
        else:
            groups.append([patch])
    disassembler = capstone.Cs(capstone.CS_ARCH_M68K,
                              capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    ranges = []
    interior = set()
    overwritten = set()
    for group in groups:
        start, end = group[0]['start'], group[-1]['end']
        decoded = []
        position = start
        for instruction in disassembler.disasm(bytes(code[start:end+12]), start):
            assert instruction.address == position
            assert instruction.id and instruction.mnemonic not in ('dc.w', 'invalid'), f'invalid instruction at {position:#x}'
            position += instruction.size
            decoded.append(dict(offset=hex(instruction.address), bytes=instruction.size,
                                instruction=instruction.mnemonic+' '+instruction.op_str))
            if position >= end:
                break
        assert position == end, f'partial instruction in patch {start:#x}..{end:#x}: decoded to {position:#x}'
        # Non-NOP patch starts remain intended entry points even when adjacent.
        entries = {p['start'] for p in group if p['command'] != 'NOP'} | {start}
        interior.update(i for i in range(start, end) if i not in entries)
        overwritten.update(range(start, end))
        ranges.append(dict(start=hex(start), end=hex(end), instructions=decoded,
                           patches=group))
    relocation_set = set(relocations)
    references = []
    candidates_scanned = 0
    for offset in range(0, len(code)-6, 2):
        word = struct.unpack_from('>H', code, offset)[0]
        target, kind = None, None
        if word & 0xf000 == 0x6000:
            displacement = word & 255
            if displacement == 0:
                displacement = struct.unpack_from('>h', code, offset+2)[0]
            elif displacement > 127:
                displacement -= 256
            target, kind = offset+2+displacement, 'Bcc/BSR/BRA'
        elif word & 0xf0f8 == 0x50c8:
            target = offset+2+struct.unpack_from('>h', code, offset+2)[0]
            kind = 'DBcc'
        elif word in (0x4eba, 0x4efa):
            target = offset+2+struct.unpack_from('>h', code, offset+2)[0]
            kind = 'PC-relative JSR/JMP'
        elif word in (0x4eb9, 0x4ef9) and (offset+2, 0) in relocation_set:
            target = struct.unpack_from('>I', code, offset+2)[0]
            kind = 'absolute JSR/JMP'
        if target is not None:
            candidates_scanned += 1
            if target in interior and offset not in overwritten:
                references.append(dict(kind=kind, source=hex(offset), target=hex(target)))
    pointer_count = 0
    for hunk, (body, relocations) in enumerate(original):
        for offset, target_hunk in relocations:
            if target_hunk != 0:
                continue
            pointer_count += 1
            target = struct.unpack_from('>I', body, offset)[0]
            if target in interior:
                references.append(dict(kind='relocated code pointer', hunk=hunk,
                                       source=hex(offset), target=hex(target)))
    assert not references, f'potential patch-interior entries: {references}'
    return dict(patches=len(patches), merged_ranges=len(ranges),
                conservative_direct_branch_candidates=candidates_scanned,
                relocated_code_pointers=pointer_count, interior_entries=references,
                ranges=ranges,
                scope='Native direct entries only; computed indirect targets and replacement semantics require separate checks.')


def installed(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'capture/listing build mismatch'
    patches = compiled_patches(listing)
    meta = {key: int(value, 0) for key, value in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    slave = slave_code(folder/'slave.slave')
    base = locate(memory, slave, meta['base'], header=32)
    assert base is not None, 'loaded slave not found'
    for patch in patches:
        command, argument = patch['command'], patch['argument']
        if command in ('P', 'PS', 'PSS'):
            target = int(argument.split()[0].removeprefix('slave:'), 16)
            expected = bytes.fromhex('4ef9' if command == 'P' else '4eb9')
            expected += struct.pack('>I', base+target)
            if command == 'PSS':
                count = int(argument.split('nops=')[1])
                assert count % 2 == 0
                expected += bytes.fromhex('4e71')*(count//2)
        elif command == 'NOP':
            count = int(argument, 16)
            assert count % 2 == 0
            expected = bytes.fromhex('4e71')*(count//2)
        else:
            assert command in ('B', 'W', 'L')
            expected = bytes.fromhex(argument)
            if command == 'B':
                expected = expected[-1:]
        assert len(expected) == patch['end']-patch['start']
        start = meta['code']-meta['base']+patch['start']
        assert memory[start:start+len(expected)] == expected, f'installed patch mismatch at {patch["start"]:#x}'
    return dict(verified_installed_patches=len(patches))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('listing', type=Path, help='exact retained listing with sibling .slave')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--capture', type=Path, help='also verify each installed patch byte and destination')
    args = parser.parse_args()
    result = audit(args.listing)
    if args.capture:
        result['installation'] = installed(args.capture, args.listing)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'ranges'}, indent=2))
