#!/usr/bin/env python3
"""Build both local 1.1b distributions, changing only Slave and ReadMe entries."""
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import tempfile
from datetime import datetime

from slave_info import code_hunk, header

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = (
    ('LegendsOfValour.lha', 'LegendsOfValour-1.1b.lha', 'LegendsOfValourHd'),
    ('LegendsOfValour_v1.0_0837.lha', 'LegendsOfValour_v1.1b_0837.lha', 'LegendsOfValour'),
)


def records(data):
    """Read level 0/1 record boundaries without decompressing or rewriting them."""
    result = {}
    pos = 0
    while pos < len(data) and data[pos]:
        start = pos
        size = data[pos] + 2
        base = data[pos:pos + size]
        if len(base) != size or size < 24 or base[20] not in (0, 1):
            raise ValueError('Expected an LHA level 0/1 header')
        if sum(base[2:]) & 255 != base[1]:
            raise ValueError('Bad LHA header checksum')
        packed = struct.unpack_from('<I', base, 7)[0]
        name = base[22:22 + base[21]].decode('latin1')
        pos += size
        end = pos + packed
        if end > len(data):
            raise ValueError('Truncated LHA entry')
        directory = ''
        if base[20] == 1:
            length = struct.unpack_from('<H', base, size - 2)[0]
            cursor = pos
            while length:
                if length < 3 or cursor + length > end:
                    raise ValueError('Invalid extended header')
                ext = data[cursor:cursor + length]
                if ext[0] == 1:
                    name = ext[1:-2].decode('latin1')
                elif ext[0] == 2:
                    directory = ext[1:-2].decode('latin1').replace('\xff', '/')
                cursor += length
                length = struct.unpack_from('<H', ext, len(ext) - 2)[0]
        name = (directory + name).replace('\\', '/')
        if name in result or name.startswith('/') or '..' in PurePosixPath(name).parts:
            raise ValueError(f'Unsafe or duplicate archive path: {name}')
        result[name] = data[start:end]
        pos = end
    if data[pos:] != b'\0':
        raise ValueError('Expected one archive terminator')
    return result


def crc16(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xa001 if crc & 1 else 0)
    return crc


def stored_record(name, content):
    """Standard -lh0- record; no external LHA compressor is required."""
    name = name.replace('/', '\\').encode('latin1')
    if len(name) > 231:
        raise ValueError('Path too long for level 0')
    now = datetime.now()
    stamp = ((now.year - 1980) << 25 | now.month << 21 | now.day << 16 |
             now.hour << 11 | now.minute << 5 | now.second // 2)
    body = (b'-lh0-' + struct.pack('<III', len(content), len(content), stamp) +
            bytes((0x20, 0, len(name))) + name + struct.pack('<H', crc16(content)))
    return bytes((len(body), sum(body) & 255)) + body + content


def read_member(lha, archive, name):
    return subprocess.run([lha, 'pq', str(archive), name], check=True,
                          stdout=subprocess.PIPE).stdout


def main():
    lha = shutil.which('lha')
    if not lha:
        raise SystemExit('Install lha/lhasa (archive reading and CRC verification).')
    originals = [(ROOT / 'tmp' / src, dst, prefix) for src, dst, prefix in PACKAGES]
    for archive, _, _ in originals:
        if not archive.is_file():
            raise SystemExit(f'Missing input archive: {archive}')
    build = ROOT / 'tmp/build-release'
    subprocess.run(['make', '-C', str(ROOT / 'whdload'), 'all',
                    'OUT=../tmp/build-release', 'VASMFLAGS='], check=True)
    slave_path = build / 'LegendsOfValour.Slave'
    slave = slave_path.read_bytes()
    info = header(code_hunk(slave_path)[0])
    expected = 'C1:B:Character creation;C2:X:Frame-independent game timing:6;'
    if info['ws_config'] != expected or 'Version 1.1b ' not in info['ws_info']:
        raise SystemExit('Expected the version 1.1b release slave with two options')
    notes = (ROOT / 'whdload/ReadMe-1.1b.txt').read_bytes()
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    # Stage and validate both before publishing either. All temporary bytes stay in tmp/.
    with tempfile.TemporaryDirectory(prefix='release-', dir=ROOT / 'tmp') as temp:
        ready = []
        for archive, output, prefix in originals:
            original = records(archive.read_bytes())
            slave_name, readme_name = f'{prefix}/LegendsOfValour.Slave', f'{prefix}/ReadMe'
            if not {slave_name, readme_name} <= original.keys():
                raise ValueError(f'Missing replacement entries in {archive}')
            old_readme = read_member(lha, archive, readme_name)
            old_requirement = b'The installed program requires 0.5 MB ChipMem and 0.5 MB OtherMem.'
            if old_readme.count(old_requirement) != 1:
                raise ValueError('Original ReadMe memory requirement has changed; review it')
            old_readme = old_readme.replace(old_requirement,
                b'The slave reserves 512 KiB ChipMem and 656 KiB OtherMem.\n'
                b' Additional memory is needed by WHDLoad and optional features.')
            replacements = {slave_name: slave, readme_name: notes + b'\n' + old_readme}
            updated = {name: stored_record(name, replacements[name])
                       if name in replacements else raw for name, raw in original.items()}
            path = Path(temp) / output
            path.write_bytes(b''.join(updated.values()) + b'\0')
            check = records(path.read_bytes())
            if list(check) != list(original):
                raise ValueError('Archive entry names or order changed')
            for name, raw in original.items():
                if name not in replacements and check[name] != raw:
                    raise ValueError(f'Unchanged entry was modified: {name}')
            subprocess.run([lha, 'tq', str(path)], check=True, stdout=subprocess.PIPE)
            for name, content in replacements.items():
                if read_member(lha, path, name) != content:
                    raise ValueError(f'Replacement extraction mismatch: {name}')
            ready.append((path, destination / output))
            print(f'Verified {output}: {len(check)} entries; only Slave and ReadMe replaced', flush=True)
        for source, target in ready:
            os.replace(source, target)
            print(target)


if __name__ == '__main__':
    main()
