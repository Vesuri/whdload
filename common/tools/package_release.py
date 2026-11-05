"""Repack a game's original release archives with the new slaves -> dist/ (ignored).

    common/dist.sh            (make dist)

Driven by the game's release/release.json:

    {
      "archives": [
        {
          "input": "TheirFinestHour.lha",
          "output": "TheirFinestHour-{version}.lha",
          "replace": {
            "TheirFinestHour/TheirFinestHour.Slave": "build:TheirFinestHour",
            "TheirFinestHour/ReadMe": "release/ReadMe"
          },
          "add": {},
          "remove": [],
          "source": {"dir": "TheirFinestHour/src", "variants": ["TheirFinestHour"]}
        }
      ]
    }

- input: a file named in inputs.sha256, taken from tmp/archives/.
- output: the file name in dist/; {version} is the release version from the first replaced
  slave's $VER string: the word before its date ("$VER: Name.Slave 1.2b (date)" and
  "$VER: Name WHDLoad Slave 1.2b (date)" give 1.2b), else the word after a one-word name.
- replace / add: archive member -> "build:<Variant>" (that variant's release slave) or a
  path relative to the game directory. A replaced member must exist in the original and an
  added one must not. remove: members to drop.
- source (optional): the archive's slave source drawer. Its files are replaced by exactly
  the game's src/ files the listed variants' release builds were assembled from (the .deps
  lists), keeping src/-relative paths in the files' own spelling (an include may name a
  file in another case). Only an archive that already ships source gets one.

Checks: every replaced slave and ReadMe must differ from the original, a replaced ReadMe
must mention the version, the archive must pass `lha t`, and its extraction must hold
exactly the original members plus the added ones minus the removed ones, each equal to
the staged file and every untouched member byte-identical to the original.
"""
import argparse
import filecmp
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LHA = os.environ.get('LHA', os.path.expanduser('~/.local/share/amiga/lha-compressor/src/lha'))


def files(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())


def extract(archive, into):
    into.mkdir(parents=True)
    subprocess.run([LHA, f'xqw={into}', str(archive)], check=True)


def version_of(slave):
    data = slave.read_bytes()
    m = (re.search(rb'\$VER: [^\x00\n(]*? (\d[^\s\x00]*) \(', data)
         or re.search(rb'\$VER: \S+ (\d[^\s\x00]*)', data))
    if not m:
        sys.exit(f'{slave}: no "$VER: <name> <version> (<date>)" string')
    return m.group(1).decode('latin-1')


def true_case(root, rel):
    """rel (a path under root) in the spelling the directory entries have. vasm reports an
    include as the source wrote it, which on a case-insensitive disk may differ."""
    path = root
    for part in Path(rel).parts:
        names = {n.lower(): n for n in os.listdir(path)}
        path = path / names.get(part.lower(), part)
    return str(path.relative_to(root))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game-root', required=True, type=Path)
    ap.add_argument('--dist', required=True, type=Path)
    ap.add_argument('--variants', required=True, help="the game's VARIANTS")
    ap.add_argument('--force', action='store_true', help='replace an existing dist file')
    args = ap.parse_args()
    root = args.game_root.resolve()
    variants = args.variants.split()
    spec = json.loads((root / 'release/release.json').read_text())
    build = root / 'tmp/build/release'
    args.dist.mkdir(parents=True, exist_ok=True)

    def source_of(value):
        if value.startswith('build:'):
            variant = value[len('build:'):]
            if variant not in variants:
                sys.exit(f'unknown variant {variant}; VARIANTS has {", ".join(variants)}')
            return build / f'{variant}.Slave'
        path = root / value
        if not path.is_file():
            sys.exit(f'no {value}')
        return path

    for entry in spec['archives']:
        original = root / 'tmp/archives' / entry['input']
        if not original.is_file():
            sys.exit(f'no tmp/archives/{entry["input"]}: run make unpack first')
        tmp = Path(tempfile.mkdtemp(prefix='dist.', dir=root / 'tmp'))
        try:
            orig_dir, stage = tmp / 'original', tmp / 'stage'
            extract(original, orig_dir)
            shutil.copytree(orig_dir, stage, symlinks=True)
            before = set(files(orig_dir))
            added, removed = set(), set()

            replace = entry.get('replace', {})
            slave_members = [m for m, v in replace.items() if v.startswith('build:')]
            if not slave_members:
                sys.exit(f'{entry["input"]}: replace names no build:<Variant> slave')
            version = version_of(source_of(replace[slave_members[0]]))

            for member, value in replace.items():
                if member not in before:
                    sys.exit(f'{entry["input"]}: no member {member} to replace')
                shutil.copyfile(source_of(value), stage / member)
            for member, value in entry.get('add', {}).items():
                if member in before:
                    sys.exit(f'{entry["input"]}: {member} exists; replace it instead')
                (stage / member).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_of(value), stage / member)
                added.add(member)
            for member in entry.get('remove', []):
                if member not in before:
                    sys.exit(f'{entry["input"]}: no member {member} to remove')
                (stage / member).unlink()
                removed.add(member)

            source = entry.get('source')
            if source:
                drawer = source['dir'].rstrip('/')
                shipped = {m for m in before if m.startswith(drawer + '/')}
                if not shipped:
                    sys.exit(f'{entry["input"]}: ships no source in {drawer}/')
                wanted = {}
                for variant in source['variants']:
                    deps = build / f'{variant}.deps'
                    if not deps.is_file():
                        sys.exit(f'no {deps.relative_to(root)}: the release build lists its sources there')
                    for dep in deps.read_text().split():
                        dep = true_case(root, dep)
                        if not dep.startswith('src/'):
                            sys.exit(f'{variant} is built from {dep}, outside src/; ship it by hand')
                        wanted[f'{drawer}/{dep[len("src/"):]}'] = root / dep
                for member in shipped - set(wanted):
                    (stage / member).unlink()
                    removed.add(member)
                for member, path in wanted.items():
                    (stage / member).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, stage / member)
                    if member not in before:
                        added.add(member)

            for member, value in replace.items():
                if filecmp.cmp(orig_dir / member, stage / member, shallow=False):
                    sys.exit(f'{member} is identical to the original')
                if Path(member).name.lower() == 'readme' and version.encode() not in (stage / member).read_bytes():
                    sys.exit(f'{member} does not mention version {version}')

            out = args.dist / entry['output'].format(version=version)
            if out.exists() and not args.force:
                sys.exit(f'{out} exists (FORCE=1 replaces it)')
            for d in sorted((p for p in stage.rglob('*') if p.is_dir()), reverse=True):
                if not any(d.iterdir()):
                    d.rmdir()
            new = tmp / out.name
            names = sorted(p.name for p in stage.iterdir())
            subprocess.run([LHA, 'a1o5q2', str(new), *names], cwd=stage, check=True)
            test = subprocess.run([LHA, 't', str(new)], capture_output=True, text=True)
            if test.returncode:
                sys.exit(f'lha t failed:\n{test.stdout}{test.stderr}')

            check = tmp / 'check'
            extract(new, check)
            got = set(files(check))
            expected = (before | added) - removed
            if got != expected:
                sys.exit(f'members differ: missing {sorted(expected - got)}, extra {sorted(got - expected)}')
            for member in sorted(got):
                if not filecmp.cmp(check / member, stage / member, shallow=False):
                    sys.exit(f'{member} differs from the staged file')
            changed = set(replace) | added | {m for m in got if source and m.startswith(source['dir'].rstrip('/') + '/')}
            for member in sorted(got - changed):
                if not filecmp.cmp(check / member, orig_dir / member, shallow=False):
                    sys.exit(f'{member} changed but was not declared')

            shutil.move(str(new), out)
            digest = hashlib.sha256(out.read_bytes()).hexdigest()
            (out.parent / (out.name + '.sha256')).write_text(f'{digest}  {out.name}\n')
            print(f'{out}  (version {version}; replaced {len(replace)}, added {len(added)}, removed {len(removed)})')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
