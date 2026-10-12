#!/usr/bin/env python3
"""Reconstruct the pinned slave as vasm source in tmp/, then prove byte identity.
The repository contains offsets and conversion rules, never the derived assembly.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import capstone

ROOT = Path(__file__).resolve().parents[1]
SLAVE_SHA = '5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986'
# Code islands established from entry, ROM/game patch destinations, filesystem
# dispatch table, callback pointers and branches. Everything else is data.
CODE = [(0,4), (0x34,0x7a), (0x4fa,0x4fe), (0x500,0x75a),
        (0x768,0x87c), (0x8de,0x8f0), (0x8f8,0x9ac), (0xa22,0x1130), (0x11bc,0x11c8),
        (0x13f0,0x14f8), (0x1524,0x15ae), (0x1696,0x17ee),
        (0x17f6,0x1cde), (0x1da4,0x1dc6)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--verify', action='store_true', help='build the CUSTOM1=2 diagnostic seam')
    modes.add_argument('--verify-control', action='store_true', help='original code with the same unused diagnostic tail/size')
    modes.add_argument('--cache-audit', action='store_true', help='VERIFY-only terminating hardware CACR audit')
    p.add_argument('--input', default='tmp/originals/cd32/WingCommanderCD32/WingCommanderCD32.Slave')
    a = p.parse_args()
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('choose a new output directory below tmp/')
    original = (ROOT/a.input).read_bytes()
    if hashlib.sha256(original).hexdigest() != SLAVE_SHA:
        raise ValueError('unsupported/changed slave; nothing overwritten')
    code = original[0x20:-4]
    assert len(code) == 0x1e0c
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_020)
    decoded = {}
    for start,end in CODE:
        pos = start
        while pos < end:
            i = next(md.disasm(code[pos:end], pos, count=1))
            assert i.mnemonic != 'dc.w' and i.size and pos+i.size <= end, hex(pos)
            mnemonic, operands = i.mnemonic, i.op_str
            if mnemonic.split(".")[0] in ("btst","bset","bclr","bchg"):
                mnemonic = mnemonic.split(".")[0]
            # MOVEM has an extension word before its PC-relative operand;
            # Capstone 5 reports a target two bytes short.
            if mnemonic.startswith('movem'):
                operands = re.sub(r'\$([0-9a-f]+)(?=\(pc)',
                                  lambda m: '$%x' % (int(m[1],16)+2), operands)
            # Capstone sign-extends a negative 16-bit PC base displacement as
            # unsigned in the 020 memory-indirect form (entry S:72).
            operands = re.sub(r'\$([0-9a-f]+)(?=, pc)',
                              lambda m: '$%x' % (int(m[1],16)&0xffff), operands)
            operands = re.sub(r'\$([0-9a-f]+)(?=\(pc|, pc)',
                              lambda m: 'slave+$'+m[1], operands)
            if mnemonic.startswith('b') and mnemonic.split('.')[0] not in ('btst','bset','bclr','bchg'):
                operands = re.sub(r'^\$([0-9a-f]+)$', r'slave+$\1', operands)
            if mnemonic.startswith('db'):
                operands = re.sub(r'\$([0-9a-f]+)$', r'slave+$\1', operands)
            # Vasm's explicit absolute size syntax.
            operands = re.sub(r'\$([0-9a-f]+)\.(w|l)', lambda m: '('+str(int(m[1],16)-(65536 if m[2]=='w' and int(m[1],16)>=32768 else 0))+').'+m[2], operands)
            if mnemonic == 'moveq':
                operands = re.sub(r'#\$([0-9a-f]+)', lambda m: '#'+str((int(m[1],16)+128)%256-128), operands)
            decoded[pos] = (i.size, mnemonic+' '+operands)
            pos += i.size
    lines = ['; Generated from the SHA-256 pinned original; keep in ignored tmp/.',
             '\torg 0', 'slave:']
    pos = 0
    while pos < len(code):
        lines += [f'\tifne *-slave-${pos:x}', '\tfail "offset drift"', '\tendif', f'S_{pos:04x}:']
        if pos in decoded:
            size, source = decoded[pos]
            if pos == 0x1422 and a.cache_audit:
                lines.append('\tbsr.w cache_audit')
            elif pos == 0x14da and a.verify:
                lines.append('\tbsr.w verify_patchseg')
            else:
                lines.append('\t'+source)
        else:
            size = min(16, len(code)-pos)
            while any(pos < x < pos+size for x in decoded):
                size -= 1
            lines.append('\tdc.b '+','.join(f'${b:02x}' for b in code[pos:pos+size]))
        pos += size
    if a.verify or a.verify_control:
        lines.append((ROOT/'whdload/verify.s').read_text())
    if a.cache_audit:
        lines.append((ROOT/'whdload/cache_audit.s').read_text())
    out.mkdir(parents=True)
    source = out/'WingCommanderCD32.s'
    source.write_text('\n'.join(lines)+'\n')
    binary = out/'payload.bin'
    subprocess.run([os.environ['VASM'], '-m68020','-spaces','-no-opt','-Fbin','-o',str(binary),str(source)],check=True)
    built = binary.read_bytes()
    if a.cache_audit:
        if built[:0x1422] != code[:0x1422] or built[0x1426:len(code)] != code[0x1426:]:
            raise ValueError('cache audit changed bytes outside the SetCPU detour')
        built = built[:0xc]+struct.pack('>H',18)+built[0xe:]
    if not (a.verify or a.cache_audit) and built[:len(code)] != code:
        differences = [hex(i) for i,(x,y) in enumerate(zip(built,code)) if x != y]
        raise ValueError(f'reassembly differs: size {len(built)}; first offsets {differences[:20]}')
    if a.verify:
        # The only original instruction replaced is S:14da..14dd. Everything
        # before/after it through the original end must still match exactly.
        if built[:0x14da] != code[:0x14da] or built[0x14de:len(code)] != code[0x14de:]:
            raise ValueError('VERIFY changed bytes outside its declared detour')
    # Standard one-code-hunk container; no original byte blob is embedded.
    header = struct.pack('>8I',0x3f3,0,1,0,0,len(built)//4,0x3e9,len(built)//4)
    result = header+built+struct.pack('>I',0x3f2)
    if not (a.verify or a.verify_control or a.cache_audit):
        assert result == original
    (out/'WingCommanderCD32.Slave').write_bytes(result)
    report = {'sha256': hashlib.sha256(result).hexdigest(), 'bytes':len(result),
              'instructions':len(decoded), 'instruction_bytes':sum(v[0] for v in decoded.values()),
              'code_ranges':CODE, 'byte_identical':result == original, 'cache_audit':a.cache_audit, 'verify':a.verify, 'verify_control':a.verify_control}
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
