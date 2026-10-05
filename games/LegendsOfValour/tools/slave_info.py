#!/usr/bin/env python3
"""Decode a WHDLoad slave without its source: header fields and patch lists.

  python3 tools/slave_info.py [SLAVE] [--pl OFF[,OFF...]]

SLAVE defaults to the installed tmp/game/LegendsOfValour/LegendsOfValour.Slave.  Offsets are
slave code-hunk offsets (the slave's own numbering; file offset = hunk offset + $20 for a
one-hunk slave).  --pl decodes the patch list starting at each offset.  Patch-list command
numbers are WHDLoad's PLCMD_* enum (whdload.i); bit 15 = 16-bit address, bit 14 = control.
"""
import argparse, os, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLAVE = os.path.join(ROOT, 'tmp/game/LegendsOfValour/LegendsOfValour.Slave')

CMDS = ['END', 'R', 'P', 'PS', 'S', 'I', 'B', 'W', 'L', 'A', 'PA', 'NOP', 'C', 'CB', 'CW', 'CL',
        'PSS', 'NEXT', 'AB', 'AW', 'AL', 'DATA', 'ORB', 'ORW', 'ORL', 'GA', 'BKPT', 'BELL',
        'IFBW', 'IFC1', 'IFC2', 'IFC3', 'IFC4', 'IFC5', 'IFC1X', 'IFC2X', 'IFC3X', 'IFC4X',
        'IFC5X', 'ELSE', 'ENDIF']
# Argument layout after the address: 'd' = word displacement to a slave label (from list start),
# 'w'/'l'/'b' = immediate, 'a' = long address.
ARGS = {'P': 'd', 'PS': 'd', 'S': 'w', 'B': 'b', 'W': 'w', 'L': 'l', 'A': 'l', 'PA': 'd',
        'NOP': 'w', 'C': 'w', 'PSS': 'dw', 'NEXT': 'd', 'AB': 'b', 'AW': 'w', 'AL': 'l',
        'ORB': 'b', 'ORW': 'w', 'ORL': 'l', 'GA': 'd', 'IFC1X': 'w', 'IFC2X': 'w', 'IFC3X': 'w',
        'IFC4X': 'w', 'IFC5X': 'w'}


def code_hunk(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'\0\0\x03\xf3', 'not a hunk file'
    n = struct.unpack_from('>I', b, 8)[0]
    off = 20 + 4 * n
    assert struct.unpack_from('>I', b, off)[0] == 0x3e9
    size = struct.unpack_from('>I', b, off + 4)[0] * 4
    return b[off + 8:off + 8 + size], off + 8


def header(h):
    w = lambda o: struct.unpack_from('>H', h, o)[0]
    l = lambda o: struct.unpack_from('>I', h, o)[0]
    s = lambda o: h[o:h.index(b'\0', o)].decode('latin1') if o else ''
    assert h[4:12] == b'WHDLOADS'
    v = w(12)
    out = {'ws_Version': v, 'ws_Flags': f'{w(14):#06x}', 'ws_BaseMemSize': f'{l(16):#x}',
           'ws_ExecInstall': l(20), 'ws_GameLoader': f'{w(24):#x}', 'ws_CurrentDir': s(w(26)),
           'ws_DontCache': w(28), 'ws_keydebug': f'{h[30]:#x}', 'ws_keyexit': f'{h[31]:#x}'}
    if v >= 8: out['ws_ExpMem'] = f'{l(32):#x}'
    if v >= 10: out.update(ws_name=s(w(36)), ws_copy=s(w(38)), ws_info=s(w(40)).replace('\n', ' | '))
    if v >= 16: out.update(ws_kickname=s(w(42)), ws_kicksize=f'{l(44):#x}', ws_kickcrc=f'{w(48):#06x}')
    if v >= 17: out['ws_config'] = s(w(50)) if w(50) else ''
    return out


def patchlist(h, start):
    o, out = start, []
    while True:
        c = struct.unpack_from('>H', h, o)[0]; o += 2
        name = CMDS[c & 0x3fff] if (c & 0x3fff) < len(CMDS) else f'?{c:#x}'
        if c == 0:
            out.append('PL_END'); return out
        if c & 0x4000:
            out.append(f'PL_{name}' + (f' {struct.unpack_from(">H", h, o)[0]:#x}' if name in ARGS else ''))
            o += 2 if name in ARGS else 0
            continue
        if c & 0x8000:
            a = struct.unpack_from('>H', h, o)[0]; o += 2
        else:
            a = struct.unpack_from('>I', h, o)[0]; o += 4
        args = []
        for k in ARGS.get(name, ''):
            if k == 'd':
                d = struct.unpack_from(">h", h, o)[0]; o += 2
                args.append(f'slave+{start + d:#x}')
            elif k == 'w':
                args.append(f'{struct.unpack_from(">H", h, o)[0]:#x}'); o += 2
            elif k == 'b':
                args.append(f'{h[o + 1]:#x}'); o += 2
            elif k == 'l':
                args.append(f'{struct.unpack_from(">I", h, o)[0]:#x}'); o += 4
        if name == 'DATA':
            n = struct.unpack_from('>H', h, o)[0]; o += 2
            args.append(h[o:o + n].hex()); o += (n + 1) & ~1
        out.append(f'PL_{name} {a:#07x}' + (', ' + ', '.join(args) if args else ''))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('slave', nargs='?', default=SLAVE)
    p.add_argument('--pl', default='')
    a = p.parse_args()
    h, foff = code_hunk(a.slave)
    print(f'# {a.slave}: code hunk {len(h):#x} bytes at file offset {foff:#x}')
    for k, v in header(h).items():
        print(f'{k:16s} {v}')
    for s in filter(None, a.pl.split(',')):
        print(f'\n## patch list at slave+{int(s, 16):#x}')
        for line in patchlist(h, int(s, 16)):
            print('  ' + line)


if __name__ == '__main__':
    main()
