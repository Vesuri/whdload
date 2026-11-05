#!/usr/bin/env python3
"""Build the release archive from the original installer, changing only declared entries.

    make dist        (game.sh game_dist; --dist names the output directory, --force
                      replaces an existing archive)

Input: tmp/archives/LegendsOfValour.lha (make unpack). Output, in the repository's dist/:
LegendsOfValourEnhanced-<version>-<YYYYMMDD>.lha and its .sha256, the version and date
from the release slave's $VER string. Replaced: the Slave, the ReadMe and the six game
icons (CUSTOM2=64 appended to their tooltypes); every other record is copied byte for byte.
"""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime

from icon import parse, with_tooltype
from slave_info import code_hunk, header

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
from package_release import date_of, version_of  # noqa: E402

INPUT = 'LegendsOfValour.lha'
PREFIX = 'LegendsOfValourHd'
OUTPUT = 'LegendsOfValourEnhanced-{version}-{date}.lha'
# The installer offers these as the game icon; it sets the default tool, Slave and PreLoad
# and keeps the other tooltypes, so each one installs with the timing option on.
ICONS = ('inf', 'infC', 'colcfou', 'colcfou2', 'colcfou3', 'colcfou4')
TIMING = b'CUSTOM2=64'


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
    ap = argparse.ArgumentParser()
    ap.add_argument('--dist', type=Path, default=ROOT.parents[1] / 'dist')
    ap.add_argument('--force', action='store_true', help='replace an existing archive')
    args = ap.parse_args()
    lha = shutil.which('lha')
    if not lha:
        raise SystemExit('Install lha/lhasa (archive reading and CRC verification).')
    archive = ROOT / 'tmp/archives' / INPUT
    if not archive.is_file():
        raise SystemExit(f'Missing input archive: {archive} (make unpack)')
    build = ROOT / 'tmp/build/release'
    # The plain release build: no extra defines from the caller.
    subprocess.run(['make', '-s', 'slave'], cwd=ROOT, check=True,
                   env=dict(os.environ, VASM_EXTRA='', VARIANT='LegendsOfValour'))
    slave_path = build / 'LegendsOfValour.Slave'
    slave = slave_path.read_bytes()
    info = header(code_hunk(slave_path)[0])
    version, date = version_of(slave_path), date_of(slave_path)
    expected = 'C1:B:Character creation;C2:X:Frame-independent game timing:6;'
    ver_date = f'{date[6:]}.{date[4:6]}.{date[:4]}'
    if info['ws_config'] != expected or f'Version {version} ({ver_date})' not in info['ws_info']:
        raise SystemExit('Expected the release slave with two options and slv_info matching $VER')
    notes = (ROOT / 'release/ReadMe').read_bytes()
    if f'version {version} ({ver_date})'.encode() not in notes:
        raise SystemExit(f'release/ReadMe has no "version {version} ({ver_date})" history entry')
    destination = args.dist.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output = OUTPUT.format(version=version, date=date)
    target = destination / output
    if target.exists() and not args.force:
        raise SystemExit(f'{target} exists (FORCE=1 replaces it)')
    original = records(archive.read_bytes())
    slave_name, readme_name = f'{PREFIX}/LegendsOfValour.Slave', f'{PREFIX}/ReadMe'
    icon_names = [f'{PREFIX}/LegendsOfValour.{suffix}' for suffix in ICONS]
    if not {slave_name, readme_name, *icon_names} <= original.keys():
        raise ValueError(f'Missing replacement entries in {archive}')
    replacements = {slave_name: slave, readme_name: notes}
    for name in icon_names:
        icon = read_member(lha, archive, name)
        tool, entries, _, _ = parse(icon)
        if entries != [b'CUSTOM1=0'] or tool not in (b'amiga2', b'WHDLoad'):
            raise ValueError(f'{name}: unexpected tooltypes {entries}; review it')
        replacements[name] = with_tooltype(icon, TIMING)
    # Stage and validate before publishing. All temporary bytes stay in tmp/.
    with tempfile.TemporaryDirectory(prefix='release-', dir=ROOT / 'tmp') as temp:
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
            extracted = read_member(lha, path, name)
            if extracted != content or extracted == read_member(lha, archive, name):
                raise ValueError(f'Replacement extraction mismatch: {name}')
        for name in icon_names:
            if parse(read_member(lha, path, name))[1] != [b'CUSTOM1=0', TIMING]:
                raise ValueError(f'{name}: tooltypes did not read back')
        if version.encode() not in replacements[readme_name]:
            raise ValueError(f'ReadMe does not mention version {version}')
        os.replace(path, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (destination / (output + '.sha256')).write_text(f'{digest}  {output}\n')
    print(f'Verified {output}: {len(check)} entries; replaced the Slave, the ReadMe and '
          f'{len(icon_names)} icons ({TIMING.decode()})')
    print(target)


if __name__ == '__main__':
    main()
