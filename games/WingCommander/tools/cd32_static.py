#!/usr/bin/env python3
"""Verified, static-only CD32 inventory. All derived output is confined to tmp/."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or
                os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev.disasm import dis
from amigaxdev.patchlist import decode
from amitools.binfmt.hunk.HunkReader import HunkReader

ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def crc16(data):
    """WHDLoad's reflected CRC-16 (poly A001, initial zero)."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xa001 if crc & 1 else 0)
    return crc


def inventory(path, out):
    data = path.read_bytes()
    reader = HunkReader()
    require(reader.read_file(str(path)) == 0, reader.error_string)
    info = {'name': path.name, 'size': len(data), 'sha256': sha(data),
            'crc16': f'{crc16(data):04x}', 'records': [], 'hunks': []}
    index = -1
    binaries = []
    for record in reader.hunks:
        info['records'].append({k: v for k, v in record.items()
                                if k not in ('data', 'reloc', 'symbols')})
        kind = record['type_name']
        if kind not in ('HUNK_CODE', 'HUNK_DATA', 'HUNK_BSS'):
            continue
        index += 1
        item = {'index': index, 'kind': kind, 'size': record['size'],
                'allocation': reader.hunks[0]['hunks'][index],
                'file_offset': record.get('data_file_offset')}
        info['hunks'].append(item)
        if 'data' not in record:
            continue
        raw = record['data']
        require(data[item['file_offset']:item['file_offset'] + len(raw)] == raw,
                'hunk payload/file offset mismatch')
        stem = out / f'{path.name}.h{index}'
        binary = stem.with_suffix(stem.suffix + '.bin')
        binary.write_bytes(raw)
        binaries.append(raw)
        text = dis(str(binary), 0, 0, len(raw), cpu='68020')
        stem.with_suffix(stem.suffix + '.dis').write_text(text)
        strings = [f'{m.start():06x} {m[0].decode("ascii")}'
                   for m in re.finditer(rb'[\x20-\x7e]{5,}', raw)]
        stem.with_suffix(stem.suffix + '.strings').write_text('\n'.join(strings) + '\n')
        # Search every byte for hardware constants, every even byte for library
        # calls; this complements the linear sweep across embedded data islands.
        hits = []
        for pos in range(len(raw) - 3):
            value = struct.unpack_from('>I', raw, pos)[0]
            if (0xbfd000 <= value <= 0xbfffff or
                    0xdff000 <= value <= 0xdfffff or
                    0xb80000 <= value <= 0xb800ff or value == 0x6c):
                hits.append(f'{pos:06x} constant {value:08x}')
            if pos % 2 == 0:
                op, disp = struct.unpack_from('>Hh', raw, pos)
                if (op & 0xfff8) in (0x4ea8, 0x4ee8) and disp < 0:
                    hits.append(f'{pos:06x} candidate call/jump a{op & 7} {disp}')
        stem.with_suffix(stem.suffix + '.candidates').write_text('\n'.join(hits) + '\n')
    return info, binaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='new directory below tmp/')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    scratch = (ROOT / 'tmp').resolve()
    require(scratch in out.parents, 'output must be below tmp/')
    require(not out.exists(), 'output exists; choose a new directory (nothing overwritten)')
    archives = {}
    for line in (ROOT / 'manifest/inputs.tsv').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        variant, filename, expected, _ = line.split('\t')
        if variant in ('cd32', 'installer'):
            path = ROOT / 'tmp/downloads' / filename
            require(sha(path.read_bytes()) == expected, f'checksum mismatch: {filename}')
            archives[variant] = path
    require(set(archives) == {'cd32', 'installer'}, 'missing manifest entries')
    out.mkdir(parents=True)
    extracted = {}
    for variant, path in archives.items():
        dest = out / variant
        dest.mkdir()
        subprocess.run(['lha', 'xq', str(path)], cwd=dest, check=True)
        extracted[variant] = dest
    fresh = extracted['cd32'] / 'WingCommanderCD32'
    reference = ROOT / 'tmp/originals/cd32/WingCommanderCD32'
    for path in fresh.rglob('*'):
        if path.is_file():
            local = reference / path.relative_to(fresh)
            require(local.is_file() and local.read_bytes() == path.read_bytes(),
                    f'reference differs or is missing: {path.relative_to(fresh)}')
    require({p.relative_to(reference) for p in reference.rglob('*') if p.is_file()} ==
            {p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file()},
            'reference has extra files; preserved unchanged')
    slave = fresh / 'WingCommanderCD32.Slave'
    installer_slave = extracted['installer'] / 'WingCommanderHD/WingCommanderCD32.slave'
    require(slave.read_bytes() == installer_slave.read_bytes(), 'installer slave differs')
    reports = []
    for name, expected_crc in [('wing.english', 0x88e7), ('wing.german', 0xced7)]:
        path = fresh / 'data' / name
        require(crc16(path.read_bytes()) == expected_crc, f'unsupported executable: {name}')
        report, _ = inventory(path, out)
        reports.append(report)
    report, binaries = inventory(slave, out)
    reports.append(report)
    code = binaries[0]
    patches = {}
    for offset in (0x7a, 0x1f2, 0x35e, 0x15d0, 0x15e6, 0x1cde, 0x1cf4):
        entries = []
        # NEXT changes the list base; the shared decoder does not follow it.
        # Stop here and inventory the destination separately.
        for address, command, argument in decode(code, offset):
            entries.append({'offset': address, 'command': command, 'argument': argument})
            if command == 'NEXT':
                break
        patches[f'{offset:04x}'] = entries
    require(crc16(b'123456789') == 0xbb3d, 'CRC-16 check vector failed')
    for report, prefix, common in zip(reports[:2], ('15d0', '1cde'), ('15e6', '1cf4')):
        require(len(patches[common]) == 23, 'unexpected game patch count')
        size = report['hunks'][0]['size']
        for entry in patches[prefix] + patches[common]:
            cmd = entry['command']
            if cmd in ('END', 'NEXT'):
                continue
            widths = {'P': 6, 'PS': 6, 'S': 2, 'R': 2, 'W': 2, 'B': 1, 'L': 4}
            width = int(entry['argument'], 16) if cmd == 'NOP' else widths[cmd]
            require(0 <= entry['offset'] <= size - width, 'patch exceeds game hunk')
    require([len(patches[k]) - 1 for k in ('007a', '01f2', '035e')] == [54, 54, 58],
            'unexpected ROM patch counts')
    for entries in patches.values():
        for entry in entries:
            if entry['argument'].startswith('slave:'):
                require(0 <= int(entry['argument'].split(':')[1], 16) < len(code),
                        'patch helper/NEXT destination exceeds slave hunk')
    (out / 'inventory.json').write_text(json.dumps(reports, indent=2) + '\n')
    (out / 'patches.json').write_text(json.dumps(patches, indent=2) + '\n')
    # Slave data islands hide the next instruction boundary from a linear sweep.
    for start, end in ((0x34, 0x7a), (0x500, 0x75a), (0x768, 0x87c),
                       (0x13f0, 0x14f8), (0x1524, 0x15ae),
                       (0x1696, 0x17ee), (0x17f6, 0x1cde), (0x1da4, 0x1dc6)):
        (out / f'slave-{start:04x}-{end:04x}.dis').write_text(
            dis(str(out / 'WingCommanderCD32.Slave.h0.bin'), 0, start, end, cpu='68020'))
    print(f'PASS: verified archives, reference tree, identical installer slave, CRCs and hunks; {out.relative_to(ROOT)}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
