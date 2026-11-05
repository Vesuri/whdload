"""Repack the WHDLoad installer archive with the new slave and ReadMe -> dist/ (ignored).

    make dist

Input: tmp/archives/Mercenary3.lha (pinned in manifest/inputs.json). Output:
dist/Mercenary3-<version>.lha with exactly the same members. Only the slave, the ReadMe
and the two game icons (Mercenary3.inf and Mercenary3.romicon, which gain the tooltype
CUSTOM5=1 so Enhanced framerate starts checked) differ.
The ReadMe is the WHDLoad Install Template's (pinned in manifest/release-templates.json)
with release/readme-body.txt and the original ReadMe's version 1.2 history entry.
LHA names LHa for UNIX; Lhasa cannot create archives.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile

from check_inputs import main as check_inputs

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tmp/archives/Mercenary3.lha'
TOP = 'Mercenary3 Install'
SLAVE = f'{TOP}/Mercenary3.Slave'
README = f'{TOP}/ReadMe'
ICONS = [f'{TOP}/Mercenary3.inf', f'{TOP}/Mercenary3.romicon']


def members(archive):
    return subprocess.run(['lsar', str(archive)], capture_output=True, text=True,
                          check=True).stdout.splitlines()[1:]


def extract(lha, archive, into):
    subprocess.run([lha, f'xqw={into}', str(archive)], check=True)


def enhanced_icon(original):
    """Append CUSTOM5=1 to a game icon's tooltype array.

    Locate the length-prefixed WHDLoad default tool, then walk and validate the whole
    array; its stored size includes the terminating null pointer. Appending keeps the
    ROMIcon colour marker first. Image data and any bytes after the array are kept.
    """
    assert original[:2] == b'\xe3\x10'
    found = [i for m in (b'\x00\x00\x00\x08WHDLOAD\x00', b'\x00\x00\x00\x08WHDLoad\x00')
             for i in [original.find(m)] if i >= 0]
    assert len(found) == 1
    start = found[0] + 12
    size = struct.unpack_from('>I', original, start)[0]
    assert size >= 4 and size % 4 == 0
    cursor = start + 4
    entries = []
    for _ in range(size // 4 - 1):
        length = struct.unpack_from('>I', original, cursor)[0]
        cursor += 4
        value = original[cursor:cursor + length]
        assert length and len(value) == length and value.endswith(b'\0')
        entries.append(value.rstrip(b'\0').upper())
        cursor += length
    assert b'SLAVE=MERCENARY3.SLAVE' in entries
    assert not any(value.lstrip(b'(').startswith(b'CUSTOM5=') for value in entries)
    entry = b'CUSTOM5=1\0'
    addition = struct.pack('>I', len(entry)) + entry
    updated = (original[:start] + struct.pack('>I', size + 4) + original[start + 4:cursor]
               + addition + original[cursor:])
    # Removing the addition must give back every original byte, artwork included.
    assert (updated[:start] + struct.pack('>I', size) + updated[start + 4:cursor]
            + updated[cursor + len(addition):]) == original
    return updated


def template_readme():
    whdload = Path(os.environ['WHDLOAD'])
    pins = json.loads((ROOT / 'manifest/release-templates.json').read_text())
    name = 'Install Template/Xxx Install/ReadMe'
    data = (whdload / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != pins[name]:
        raise ValueError(f'WHDLoad template differs: {name}')
    return data.decode('latin-1')


def readme(version, original):
    text = template_readme()
    start = text.index(' This install applies to ')
    end = text.index(' Contact:')
    body = (ROOT / 'release/readme-body.txt').read_text(encoding='utf-8')
    if f' version {version} (' not in body:
        raise ValueError(f'release/readme-body.txt has no version {version} entry')
    old = original.decode('latin-1')
    history = old[old.index('\tversion 1.2 '):].replace('\t', ' ').rstrip()
    text = text[:start] + body + '\n' + history + '\n\n\n' + text[end:]
    return text.encode('latin-1')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--slave', type=Path, default=ROOT / 'tmp/build/Mercenary3.Slave')
    args = parser.parse_args()
    lha = os.environ['LHA']
    check_inputs()
    slave = args.slave.read_bytes()
    if b'(VERIFY)' in slave:
        raise ValueError('VERIFY build; package the release slave')
    match = re.search(rb'Version ([0-9]+\.[0-9]+[a-z]?) \(([0-9.]+)\)', slave)
    version, date = match.group(1).decode(), match.group(2).decode()
    if f' version {version} ({date}) ' not in (ROOT / 'release/readme-body.txt').read_text():
        raise ValueError(f'ReadMe entry for version {version} ({date}) is missing')

    names = members(SOURCE)
    changed = {SLAVE, README, *ICONS}
    if not changed <= set(names):
        raise ValueError('Source archive lacks the slave, ReadMe or game icons')
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    out = dist / f'Mercenary3-{version}.lha'
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
        stage, new, old = (Path(tmp) / d for d in ('stage', 'new', 'old'))
        extract(lha, SOURCE, stage)
        (stage / SLAVE).write_bytes(slave)
        (stage / README).write_bytes(readme(version, (stage / README).read_bytes()))
        for name in ICONS:
            (stage / name).write_bytes(enhanced_icon((stage / name).read_bytes()))
        out.unlink(missing_ok=True)
        subprocess.run([lha, 'a1o5q2', str(out), *names], cwd=stage, check=True)

        test = subprocess.run([lha, 't', str(out)], capture_output=True, text=True)
        if test.returncode:
            raise ValueError(test.stdout + test.stderr)
        # LHa for UNIX sorts members, so compare sorted lists.
        if sorted(members(out)) != sorted(names):
            raise ValueError('Member list differs from the source archive')
        extract(lha, out, new)
        extract(lha, SOURCE, old)
        for name in names:
            a, b = (new / name).read_bytes(), (old / name).read_bytes()
            if a != (stage / name).read_bytes():
                raise ValueError(f'Extracted member differs from staging: {name}')
            if (a != b) != (name in changed):
                raise ValueError(f'Unexpected change state: {name}')
        for path in (new, old):
            extra = {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
            if extra != set(names):
                raise ValueError(f'Extraction holds other files: {sorted(extra ^ set(names))}')
    print(f'{out.relative_to(ROOT)}: {len(names)} files, {out.stat().st_size} bytes; '
          f'changed: {", ".join(sorted(changed))}')


if __name__ == '__main__':
    main()
