#!/usr/bin/env python3
"""Read the CD32 flight pointer colour-bank snapshots (WCBank1-3).

A diagnostic slave (tools/reconstruct.py --release --bank-diag, never
released) saves them with the pointer shown for 250, 1500 and 3000 fields;
src/mouse.s (BANK_DIAG) gives the layout. Prints the counters, the copper
pointers, and every BPLCON4 move in both flight copper lists and copinit,
with what selects sprite 7's colour.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

HEADER, LIST, COPINIT = 128, 4096, 1024
SPRITE_BANK = 12
COUNTERS = ('calls', 'found', 'not_found', 'undone', 'shown', 'lof_list0', 'lof_list1',
            'lof_other', 'patched', 'unpatched', 'attach')


def moves(data, base):
    """The copper list's instructions up to its end, with their addresses."""
    out = []
    for i in range(0, len(data)-3, 4):
        a, b = struct.unpack_from('>HH', data, i)
        out.append((base+i if base else i, a, b))
        if (a, b) == (0xffff, 0xfffe):
            break
    return out


def bplcon4(insns):
    return [dict(at=f'{at:08x}', value=f'{v:04x}', osprm=v & 15, esprm=v >> 4 & 15)
            for at, reg, v in insns if reg == 0x010c]


def decode(raw):
    magic, version = struct.unpack_from('>4sI', raw, 0)
    if magic != b'WCBD' or version != 1 or len(raw) != HEADER+2*LIST+COPINIT:
        raise ValueError(f'not a version 1 WCBank file ({magic!r}, {version}, {len(raw)} bytes)')
    c = dict(zip(COUNTERS, struct.unpack_from('>11I', raw, 8)))
    index, field = struct.unpack_from('>II', raw, 52)
    lof, shf, copinit = struct.unpack_from('>3I', raw, 60)
    table = struct.unpack_from('>2I', raw, 72)
    starts = struct.unpack_from('>2I', raw, 80)
    bank = [struct.unpack_from('>IH', raw, 88+8*i) for i in range(2)]
    pos, ctl, line0 = struct.unpack_from('>HHI', raw, 104)
    ss, = struct.unpack_from('>I', raw, 112)
    last, bad = struct.unpack_from('>HH', raw, 116)
    maxcount = struct.unpack_from('>2H', raw, 120)
    image, = struct.unpack_from('>I', raw, 124)
    lists = []
    for i in range(2):
        data = raw[HEADER+i*LIST:HEADER+(i+1)*LIST]
        insns = moves(data, starts[i])
        lists.append(dict(cprlist=f'{table[i]:08x}', start=f'{starts[i]:08x}', max_count=maxcount[i],
                          instructions=len(insns), ended=insns[-1][1:] == (0xffff, 0xfffe) if insns else False,
                          is_lof=starts[i] == lof, bplcon4=bplcon4(insns),
                          found_at=f'{bank[i][0]:08x}+{bank[i][1]}'))
    ci = moves(raw[HEADER+2*LIST:], copinit)
    return dict(snapshot=index, field=field, counters=c,
                gfx=dict(lof=f'{lof:08x}', shf=f'{shf:08x}', copinit=f'{copinit:08x}'),
                lists=lists, copinit_bplcon4=bplcon4(ci),
                vbl_bplcon4=dict(last=f'{last:04x}', last_without_bank=f'{bad:04x}'),
                sprite=dict(pos=f'{pos:04x}', ctl=f'{ctl:04x}', attach=bool(ctl & 0x80), line0=f'{line0:08x}',
                            simple_sprite=f'{ss:08x}', image=f'{image:08x}', image_aligned_8=image % 8 == 0))


def verdict(d):
    c, notes = d['counters'], []
    if c['shown'] == 0:
        notes.append('the pointer was never shown in a VBL')
    if c['lof_other']:
        notes.append(f"COP2LC (GfxBase LOFlist) was neither patched list in {c['lof_other']} of {c['shown']} VBLs")
    if c['unpatched']:
        notes.append(f"the displayed list's BPLCON4 lacked bank {SPRITE_BANK} in {c['unpatched']} VBLs "
                     f"(last {d['vbl_bplcon4']['last_without_bank']})")
    if c['undone']:
        notes.append(f"the patch was undone {c['undone']} times (the list rewritten in place)")
    if c['not_found']:
        notes.append(f"{c['not_found']} searches found no BPLCON4 move")
    if c['attach']:
        notes.append(f"SPR7CTL had ATTACH in {c['attach']} VBLs")
    for i, l in enumerate(d['lists']):
        later = [m for m in l['bplcon4'][1:]]
        if later:
            notes.append(f'list {i} has {len(l["bplcon4"])} BPLCON4 moves: '
                         + ', '.join(m['value'] for m in l['bplcon4']))
        if l['bplcon4'] and l['bplcon4'][-1]['osprm'] != SPRITE_BANK:
            notes.append(f"list {i}'s last BPLCON4 move has OSPRM {l['bplcon4'][-1]['osprm']}")
    return notes or ['every check as intended: the bank reached the displayed list']


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('files', nargs='+', type=Path)
    p.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    result = []
    for f in a.files:
        d = decode(f.read_bytes())
        d['file'] = str(f)
        d['verdict'] = verdict(d)
        result.append(d)
    if a.json:
        print(json.dumps(result, indent=2))
        return 0
    for d in result:
        print(f"{d['file']}: snapshot {d['snapshot']} at field {d['field']}")
        print('  counters:', ' '.join(f'{k}={v}' for k, v in d['counters'].items()))
        print('  gfx:', d['gfx'], ' sprite:', d['sprite'])
        for i, l in enumerate(d['lists']):
            print(f"  list {i}: cprlist {l['cprlist']} start {l['start']} found {l['found_at']} "
                  f"lof={l['is_lof']} {l['instructions']} insns ended={l['ended']} BPLCON4:",
                  ' '.join(f"{m['value']}@{m['at']}" for m in l['bplcon4']))
        print('  copinit BPLCON4:', ' '.join(f"{m['value']}@{m['at']}" for m in d['copinit_bplcon4']) or 'none')
        for n in d['verdict']:
            print('  -', n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
