#!/usr/bin/env python3
"""F5: game directories that test the slave's checks of an edited f1gp, and their check.

  python3 tools/f5_variant.py site OUT
  python3 tools/f5_variant.py name OUT
  python3 tools/f5_variant.py check KIND CAPTURE

OUT (under tmp/) gets a copy of the verified stock game directory with one change to
data/f1gp:
- site: the pacer's wait branch at h0+$1288, a hook site, re-encoded as the same branch
  (BCS.W $127C becomes BCS.S $127C and NOP), so the game runs as before but the hook
  sites' sum differs: the slave must leave every developer option out.
- name: the last driver's name (h2+$2AF52 + 39 * 24) changed, as an editor would, with
  the first name kept: the slave must keep the file's names instead of the 1991 ones.
check reads a c2_capture --expect-native capture of such a directory (its memory dump
and whdl_log.txt) and prints PASS or raises.
"""
import shutil
import sys
from pathlib import Path

from f1_diff import hunks
from race_profile import game_hunks, image, locate
from slave_inputs import ROOT, verify

STOCK = ROOT/'tmp/game/FormulaOneGrandPrix4Disk'
SITE = (0, 0x1288, bytes.fromhex('6500fff2'), bytes.fromhex('65f24e71'))
NAME = (2, 0x2af52+39*24, b'F5 Edited Driver\0')
LOG = 'F1GP VERIFY F5: hook sites differ from the stock file; developer options off'


def build(kind, out):
    out = Path(out).resolve()
    if not out.is_relative_to(ROOT/'tmp'):
        raise ValueError('output must stay in project tmp/')
    verify()
    data = bytearray((STOCK/'data/f1gp').read_bytes())
    layout = {h: o for h, o, _ in hunks(bytes(data))}
    if kind == 'site':
        h, off, old, new = SITE
        at = layout[h]+off
        assert data[at:at+len(old)] == old
        data[at:at+len(new)] = new
    else:
        h, off, name = NAME
        at = layout[h]+off
        data[at:at+24] = name.ljust(24, b'\0')
    shutil.copytree(STOCK, out)
    (out/'data/f1gp').write_bytes(data)
    print(f'{out.relative_to(ROOT)}: {kind} variant')


def check(kind, capture):
    root = Path(capture)
    memory = image(*((root/(n+'.bin')).read_bytes() if (root/(n+'.bin')).exists() else b''
                     for n in ('chip', 'fast', 'slow')))
    found = locate(memory, game_hunks())
    log = (root/'whdl_log.txt').read_text(errors='replace') if (root/'whdl_log.txt').exists() else ''
    if kind == 'site':
        h, off, _, new = SITE
        at = found[h][0]+off
        assert memory[at:at+len(new)] == new, 'the changed site was patched'
        assert memory[found[0][0]+0x2cc3c:found[0][0]+0x2cc3e] != b'\x4e\xb9', 'clock hook installed'
        assert LOG in log, 'no F5 log line'
    else:
        h, off, name = NAME
        at = found[h][0]+off
        assert memory[at:at+len(name)] == name, "the file's names were replaced"
        assert LOG not in log
    print(f'F5 {kind} check PASS')


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        check(sys.argv[2], sys.argv[3])
    else:
        build(sys.argv[1], sys.argv[2])
