#!/usr/bin/env python3
"""Rebuild JOTD's two v1.5 archives with the new slave -> dist/ (LH5, level-1 headers).

    python3 tools/package_release.py

Inputs, kept local in tmp/ (never committed): JOTD's installer tmp/TestDrive2.lha and the
Retroplay preinstalled archive tmp/TestDrive2_v1.5_0588.lha. Outputs:

  dist/TestDrive2-<ver>.lha            the installer, the same members as tmp/TestDrive2.lha
  dist/TestDrive2_v<ver>_0588.lha      preinstalled, the same members as the 0588 archive

Only these members change: the slave (a fresh normal build of whdload/), the ReadMe (JOTD's
text with whdload/readme-history.txt added at the top of its History), the game icon (gains the
tooltype CUSTOM2=1, since WHDLoad options have no default) and, in the installer, source/
(the new TestDrive2HD.s plus the files it includes; the KickEmu sources and API headers are
copied from the shared $WHDLOAD). Everything else is copied byte for byte
(LHa for UNIX stores members sorted by name); the archives are re-extracted and checked. 0588 is
Retroplay's variant number, not a checksum; it is kept because the game data is unchanged. The preinstalled archive holds
the game itself: dist/ output is *.lha, which git ignores.
"""
from pathlib import Path
import os
import re
import shutil
import struct
import subprocess
import tempfile
from local_env import path

ROOT = Path(__file__).resolve().parents[1]
LHA = path('LHA')  # LHa for UNIX: Lhasa cannot create LH5 archives
INSTALLER = ROOT / 'tmp/TestDrive2.lha'
PREINSTALLED = ROOT / 'tmp/TestDrive2_v1.5_0588.lha'
WHDLOAD = Path(path('WHDLOAD'))  # the KickEmu sources and API headers the slave builds with
SOURCES = ['TestDrive2HD.s', 'simulation.s', 'simulation-patches.i', 'simulation-verify.s',
           'render.s', 'Makefile', 'whdload/kick13.s', 'whdload/kickfs.s',
           'whdload/segtracker.s', 'whdload/kick.readme', 'whdload/README.md', 'include/whdload.i',
           'include/whdmacros.i', 'include/lvo/dos.i', 'include/lvo/exec.i',
           'include/lvo/graphics.i', 'include/lvo/expansion.i']
# Shipped source files that come from $WHDLOAD rather than whdload/.
SHARED_SOURCES = {'whdload/kick13.s': 'Src/sources/whdload/kick13.s',
                  'whdload/kickfs.s': 'Src/sources/whdload/kickfs.s',
                  'whdload/segtracker.s': 'Src/sources/whdload/segtracker.s',
                  'whdload/kick.readme': 'Src/sources/whdload/kick.readme',
                  'include/whdload.i': 'Include/whdload.i',
                  'include/whdmacros.i': 'Include/whdmacros.i'}
TOOLTYPE = b'CUSTOM2=1'


def members(archive):
    return subprocess.run(['lsar', archive], capture_output=True, text=True,
                          check=True).stdout.splitlines()[1:]


def extract(archive, into):
    subprocess.run(['lha', f'xqw={into}', str(archive)], check=True)


def add_tooltype(path, tooltype):
    """Insert a tooltype after PRELOAD in an Amiga DiskObject, leaving all other bytes alone."""
    b = path.read_bytes()
    assert b[:2] == b'\xe3\x10', path
    select, = struct.unpack('>I', b[4 + 22:4 + 26])
    default_tool, tool_types = struct.unpack('>II', b[50:58])
    p = 78 + (56 if struct.unpack('>I', b[66:70])[0] else 0)
    for _ in range(2 if select else 1):
        w, h, d = struct.unpack('>HHH', b[p + 4:p + 10])
        p += 20 + (w + 15) // 16 * 2 * h * d
    if default_tool:
        p += 4 + struct.unpack('>I', b[p:p + 4])[0]
    assert tool_types, path
    start, n = p, struct.unpack('>I', b[p:p + 4])[0] // 4 - 1
    p += 4
    types = []
    for _ in range(n):
        size = struct.unpack('>I', b[p:p + 4])[0]
        types.append(b[p + 4:p + 3 + size])
        p += 4 + size
    assert tooltype not in types, path
    types.insert(types.index(b'PRELOAD') + 1, tooltype)
    table = struct.pack('>I', (len(types) + 1) * 4) + b''.join(
        struct.pack('>I', len(t) + 1) + t + b'\0' for t in types)
    path.write_bytes(b[:start] + table + b[p:])


def readme(original):
    entry = (ROOT / 'whdload/readme-history.txt').read_bytes().replace(b'\n', b'\r\n')
    key = b'History:\r\n\r\n'
    assert original.count(key) == 1 and entry not in original
    return original.replace(key, key + entry)


def archive(stage, names, out):
    out.unlink(missing_ok=True)
    subprocess.run([LHA, 'a1o5q2', str(out), *names], cwd=stage, check=True)
    test = subprocess.run([LHA, 't', str(out)], capture_output=True, text=True)
    assert test.returncode == 0, test.stdout + test.stderr
    with tempfile.TemporaryDirectory() as check:
        extract(out, check)
        for name in names:
            assert (Path(check) / name).read_bytes() == (stage / name).read_bytes(), name
    assert sorted(members(out)) == sorted(names), out  # LHa for UNIX sorts the members
    print(f'{out.relative_to(ROOT)}: {len(names)} files, {out.stat().st_size} bytes')


def main():
    subprocess.run(['make', '-C', str(ROOT / 'whdload')], check=True, capture_output=True)
    slave = (ROOT / 'whdload/TestDrive2.slave').read_bytes()
    assert b'C5:' not in slave, 'VERIFY build'
    version = re.search(rb'\$VER: slave ([0-9.a-z]+)', slave).group(1).decode()
    assert version.encode() in (ROOT / 'whdload/readme-history.txt').read_bytes()
    (ROOT / 'dist').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / 'installer'
        extract(INSTALLER, stage)
        names = members(INSTALLER)
        top = stage / 'TestDrive2Install'
        (top / 'TestDrive2.slave').write_bytes(slave)
        (top / 'readme').write_bytes(readme((top / 'readme').read_bytes()))
        add_tooltype(top / 'TestDrive2.exoticon', TOOLTYPE)
        at = names.index('TestDrive2Install/source/TestDrive2HD.s')
        names[at + 1:at + 1] = [f'TestDrive2Install/source/{s}' for s in SOURCES[1:]
                               if f'TestDrive2Install/source/{s}' not in names]
        for s in SOURCES:
            destination = top / 'source' / s
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = WHDLOAD / SHARED_SOURCES[s] if s in SHARED_SOURCES else ROOT / 'whdload' / s
            shutil.copyfile(source, destination)
        archive(stage, names, ROOT / f'dist/TestDrive2-{version}.lha')

        stage = Path(tmp) / 'preinstalled'
        extract(PREINSTALLED, stage)
        names = members(PREINSTALLED)
        top = stage / 'TestDrive2'
        assert (top / 'data/duel').stat().st_size == 108868, 'duel v1'
        (top / 'TestDrive2.slave').write_bytes(slave)
        (top / 'ReadMe').write_bytes(readme((top / 'ReadMe').read_bytes()))
        add_tooltype(top / 'TestDrive2.info', TOOLTYPE)
        archive(stage, names, ROOT / f'dist/TestDrive2_v{version}_0588.lha')


if __name__ == '__main__':
    main()
