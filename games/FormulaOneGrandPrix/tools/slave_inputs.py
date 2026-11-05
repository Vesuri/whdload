#!/usr/bin/env python3
"""Verify local inputs; reconstruct the original slave and extract its names payload.

Run after sourcing amiga/env.sh. Generated source contains derived bytes and must stay
under tmp/. The original loader is symbolic assembly; the old KickEmu is a separate
opaque section, replaced by the shared source in the new slave.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SLAVE = 'tmp/game/FormulaOneGrandPrix4Disk/FormulaOneGrandPrix4Disk.Slave'
CODE = ((0x170, 0x2a6), (0x358, 0x3a4), (0x3b6, 0x424))


def verify():
    pins = json.loads((ROOT / 'manifest/game-inputs.json').read_text())
    for name, digest in pins.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'input hash mismatch: {name}')


def prepare():
    verify()
    out = ROOT / 'tmp/slave'
    out.mkdir(parents=True, exist_ok=True)
    whole = (ROOT / SLAVE).read_bytes()
    # Single HUNK_CODE, no relocations; reject a different executable wrapper.
    import struct
    assert struct.unpack_from('>7I', whole) == (1011, 0, 1, 0, 0, 1357, 1001)
    assert struct.unpack_from('>I', whole, 28)[0] == 1357
    b = whole[32:32 + 5428]
    assert whole[32 + 5428:] == b'\x00\x00\x03\xf2'
    (out / 'original.bin').write_bytes(b)
    (out / 'names.rnc').write_bytes(b[0x424:0x6eb])
    tool = Path(os.environ.get('AMIGA_TOOLCHAIN', Path.home()/'.local/opt'))/'bin/m68k-amiga-elf-objdump'
    text = '\n'.join(subprocess.check_output([str(tool), '-D', '-b', 'binary', '-m', 'm68k:68000',
                        f'--start-address={a}', f'--stop-address={z}',
                        str(out/'original.bin')], text=True) for a,z in CODE)
    insns = {}
    for line in text.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s*([0-9a-f ]+)\t\s*(.+)', line)
        if m:
            o = int(m[1], 16)
            if any(a <= o < z for a, z in CODE):
                insns[o] = m[3]
    labels = {a for a, _ in CODE}
    for ins in insns.values():
        labels.update(int(x,16) for x in re.findall(r'0x([0-9a-f]+)\(pc\)', ins))
        if re.match(r'^(?:b(?:ra|sr|eq|ne|hi|ls|cc|cs|pl|mi|vc|vs|ge|lt|gt|le)|db\w+)\.', ins):
            labels.update(int(x,16) for x in re.findall(r'0x([0-9a-f]+)', ins))
    labels.update((0, 0x2a6, 0x2dc, 0x312, 0x424, 0x6ec, len(b)))
    lines = ['; Generated locally from the pinned original; never commit this file.',
             '; Loader code is assembly; data and old KickEmu remain literal bytes.']
    for p in range(len(b)):
        if p in labels:
            lines.append(f'L{p:04x}:')
        if p in insns:
            ins = insns[p]
            ins = re.sub(r'0x([0-9a-f]+)\(pc\)', lambda m:f'L{int(m[1],16):04x}(pc)', ins)
            if re.match(r'^(?:b(?:ra|sr|eq|ne|hi|ls|cc|cs|pl|mi|vc|vs|ge|lt|gt|le)|db\w+)\.', ins):
                ins = re.sub(r'0x([0-9a-f]+)', lambda m:f'L{int(m[1],16):04x}', ins)
            ins = re.sub(r'0x([0-9a-f]+)', r'$\1', ins)
            # objdump prints sign-extended absolute-short operands without a suffix.
            ins = re.sub(r'\$ffffffff', '-1.w', ins)
            ins = ins.replace('$4,a6', '$4.w,a6')
            if ins == 'pea $9':
                ins = 'pea $9.w'
            lines.append('        '+ins)
        elif any(a <= p < z for a,z in CODE):
            continue
        else:
            lines.append(f'        dc.b ${b[p]:02x}')
    lines.append(f'L{len(b):04x}:')
    (out/'original.s').write_text('\n'.join(lines)+'\n')
    print('Verified inputs; wrote tmp/slave/original.s and names.rnc')


if __name__ == '__main__':
    prepare()
