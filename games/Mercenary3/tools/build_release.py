"""Adapt verified WHDLoad templates into a new, ignored install drawer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

from check_inputs import main as check_inputs

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Template anchor is not unique: {old!r}')
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--slave', type=Path, default=ROOT / 'tmp/build/Mercenary3.Slave')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'tmp') or out.exists():
        parser.error('output must be a new directory under tmp/')
    check_inputs()
    whdload = Path(os.environ['WHDLOAD'])
    templates = {}
    for name, expected in json.loads((ROOT / 'manifest/release-templates.json').read_text()).items():
        data = (whdload / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'WHDLoad template differs: {name}')
        templates[Path(name).name] = data.decode('latin-1')
    original = ROOT / 'tmp/installer/Mercenary3/Mercenary3 Install'
    slave = args.slave.read_bytes()
    if b'Version 2.0 (23.10.2026)' not in slave or b'(VERIFY)' in slave:
        raise ValueError('Build the version 2.0 release slave first')

    readme = templates['ReadMe']
    start = readme.index(' This install applies to ')
    end = readme.index(' Contact:')
    history = (original / 'ReadMe').read_text(encoding='latin-1')
    history = history[history.index('\tversion 1.2'):].replace('\t', ' ').rstrip()
    body = (ROOT / 'whdload/release/readme-body.txt').read_text()
    readme = readme[:start] + body + history + '\n\n\n' + readme[end:]

    install = templates['Install']
    install = replace_once(install, '(set #version 3)', '(set #version 0)')
    install = replace_once(install, '(set #sol-file "Solution")', '(set #sol-file "Transports")')
    # Retain the original install's complete solution tree, including HTML pictures.
    install = replace_once(install, '(set #dest-org #dest)', '''(copyfiles
  (help @copyfiles-help)
  (source "")
  (dest #dest)
  (pattern "Sol#?")
)
(set #dest-org #dest)''')
    install = replace_once(install, '(set #icon_set_slave_preload "")',
                           '(set #icon_set_slave_preload "true")')
    install = replace_once(install, '(settooltype "PreLoad" "")',
                           '(settooltype "PreLoad" "")\n    (settooltype "Cache" "")')
    install = '; Mercenary 3 install version 2.0 (23.10.2026)\n' + install

    # Keep the verified input drawer intact. No game image is included.
    out.mkdir(parents=True)
    dest = out / 'Mercenary3 Install'
    shutil.copytree(original, dest, ignore=shutil.ignore_patterns('src', '*.uaem'))
    shutil.copy2(original.parent / 'Mercenary3 Install.info', out)
    (dest / 'Install').write_bytes(install.encode('latin-1'))
    (dest / 'ReadMe').write_bytes(readme.encode('latin-1'))
    (dest / 'Mercenary3.Slave').write_bytes(slave)
    print(f'Release prepared: {dest.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
