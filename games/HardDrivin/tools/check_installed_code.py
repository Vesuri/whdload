"""Compare the game code two slaves install (plan step G4).

check_installed_code.py NEW-RUN OLD.slave OLD.lst NEW.slave NEW.lst --custom1 N [--profile P]

Boots each slave in the FS-UAE harness to the title wait ($8520) with
CUSTOM1=N and dumps the live game code hunk. Every byte must be equal,
except the 32-bit operands of JSR/JMP abs.l (patch calls into the slave):
there both targets must be the same slave label, found through each slave's
listing. A larger slave also loads the game at another base, so absolute
addresses into the game's own hunks may differ by exactly that offset. NEW-RUN is a new directory below tmp/prof.
"""
import argparse
import bisect
import json
import os
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from capture_demo import ROOT                 # noqa: E402
from capture_session import Session           # noqa: E402
from check_handling_step import code_hunk     # noqa: E402

CODE_SIZE = 0x12d3c
GAME_SPAN = 0x30000           # code, data and BSS allocations, with LoadSeg links


def labels(listing):
    """(offset, name) of every global label in section 0, sorted."""
    out, pending = [], []
    addr = re.compile(r'^00:([0-9A-F]{8}) ')
    lab = re.compile(r'^\s+\d+: ([A-Za-z_][A-Za-z0-9_]*):')
    for line in open(listing, encoding='latin-1'):
        m = lab.match(line[28:]) if len(line) > 28 else None
        if m:
            pending.append(m.group(1))
        a = addr.match(line)
        if a and pending:
            out += [(int(a.group(1), 16), p) for p in pending]
            pending = []
    out.sort()
    return out


def name_at(table, off):
    i = bisect.bisect_right(table, (off, '￿')) - 1
    if i < 0:
        return None
    base, name = table[i]
    return name if base == off else '%s+%d' % (name, off - base)


def capture(out, slave, custom1, profile):
    if (out / 'title.json').exists():
        meta = json.loads((out / 'title.json').read_text())
        return (out / 'title-code.bin').read_bytes(), meta['code_base'], meta['slave_base']
    out.mkdir()
    shutil.copyfile(slave, out / 'slave.slave')
    s = Session(out, profile, out / 'slave.slave', 0x8520)
    s.env['WHD_ARGS'] += ' CUSTOM1=%d' % custom1
    try:
        s.boot()
        images = s.dump_banks('title')
    finally:
        s.close()
    code_base = s.layout['code_base']

    def read(a, n):
        for base, b in images:
            if base <= a and a + n <= base + len(b):
                return b[a - base:a - base + n]
        raise ValueError(hex(a))
    # WHDLoad rewrites header fields; find the slave by a block of its code
    probe = code_hunk(slave)[0x100:0x140]
    hits = [base + b.find(probe) - 0x100 for base, b in images if b.find(probe) >= 0]
    assert len(hits) == 1, 'slave image found %d times' % len(hits)
    (out / 'title-code.bin').write_bytes(read(code_base, CODE_SIZE))
    (out / 'title.json').write_text(json.dumps(dict(code_base=code_base, slave_base=hits[0])) + '\n')
    return read(code_base, CODE_SIZE), code_base, hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('old_slave')
    ap.add_argument('old_listing')
    ap.add_argument('new_slave')
    ap.add_argument('new_listing')
    ap.add_argument('--custom1', type=int, required=True)
    ap.add_argument('--profile', default='a500')
    a = ap.parse_args()
    paths = [os.path.abspath(p) for p in (a.old_slave, a.old_listing, a.new_slave, a.new_listing)]
    os.chdir(ROOT)
    out = ROOT / 'tmp/prof' / a.name
    out.mkdir(exist_ok=True)
    old, old_code, old_slave = capture(out / 'old', paths[0], a.custom1, a.profile)
    new, new_code, new_slave = capture(out / 'new', paths[2], a.custom1, a.profile)
    old_labels, new_labels = labels(paths[1]), labels(paths[3])
    diffs = [i for i in range(CODE_SIZE) if old[i] != new[i]]
    calls, relocated, bad, done = [], 0, [], set()

    def long(b, at):
        return struct.unpack('>I', b[at:at + 4])[0]

    def in_game(o, n):
        # code, data and BSS hunks: the game loads as a whole at another base
        return 0 <= o - old_code < GAME_SPAN and o - old_code == n - new_code

    for i in diffs:
        if i in done:
            continue
        # a JSR/JMP abs.l whose operand covers byte i
        for at in range(i - 5, i - 1):
            if at >= 0 and old[at:at + 2] in (b'\x4e\xb9', b'\x4e\xf9') and new[at:at + 2] == old[at:at + 2]:
                break
        else:
            at = None
        if at is not None:
            o, n = long(old, at + 2), long(new, at + 2)
            if in_game(o, n):
                relocated += 1
                done.update(range(at + 2, at + 6))
                continue
            lo, ln = name_at(old_labels, o - old_slave), name_at(new_labels, n - new_slave)
            calls.append(dict(offset=hex(at), old=lo, new=ln))
            done.update(range(at + 2, at + 6))
            if lo != ln or lo is None or '+' in lo:
                bad.append(i)
            continue
        # any other absolute address into the game, moved with its base
        for w in range(i - 3, i + 1):
            if w >= 0 and in_game(long(old, w), long(new, w)):
                relocated += 1
                done.update(range(w, w + 4))
                break
        else:
            bad.append(i)
    result = dict(custom1=a.custom1, profile=a.profile, differing_bytes=len(diffs),
                  patch_calls_relocated=len(calls), game_addresses_relocated=relocated, unexplained=[hex(i) for i in bad[:50]],
                  old_code_base=hex(old_code), new_code_base=hex(new_code),
                  old_slave_base=hex(old_slave), new_slave_base=hex(new_slave), calls=calls)
    (out / 'installed-code.json').write_text(json.dumps(result, indent=2) + '\n')
    if bad:
        print('CUSTOM1=%d: %d bytes differ outside relocated patch calls, or a call target '
              'changed: %s' % (a.custom1, len(bad), result['unexplained'][:10]))
        sys.exit(1)
    print('CUSTOM1=%d: the game code (%d bytes) is identical apart from %d patch calls into the '
          'slave, each to the same label, and %d addresses into the game, which loads %+#x away '
          '(%d bytes)' % (a.custom1, CODE_SIZE, len(calls), relocated, new_code - old_code, len(diffs)))


if __name__ == '__main__':
    main()
