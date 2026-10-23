#!/usr/bin/env python3
"""Adversarial B4 checks against actual off/on captures; all fixtures stay in tmp/."""
import json
import shutil
import tempfile
import re
import sys
from pathlib import Path
from check_disabled import ROOT, SOURCE, check, ranges


def main():
    source=SOURCE.read_text()
    declaration='; PERF_RANGE h0:3c9d2 6 custom=5 bit=0 variant=582992'
    bad_sources={
        'undeclared option':source.replace('C5:X:Verify pacer relay:0;', ''),
        'missing annotation':source.replace(declaration,''),
        'wrong range size':source.replace('h0:3c9d2 6','h0:3c9d2 4'),
        'wrong hook address':source.replace('PL_PS $3c9d2,','PL_PS $3c9d4,'),
        'wrong bit':source.replace('custom=5 bit=0','custom=5 bit=1'),
        'malformed annotation':source.replace('PERF_RANGE h0:','PERF_RANGE h:'),
        'extra unannotated hook':source.replace('        PL_ENDIF','        PL_PS $3c9d8,verify_pacer\n        PL_ENDIF'),
        'orphan annotation':source.replace('        PL_PS $3c9d2,verify_pacer',''),
        'empty inventory':re.sub(r'; PERF_RANGE[^\n]+\n\s*PL_(?:P(?:S)?|NOP|R)[^\n]+', '', source),
    }
    for name,text in bad_sources.items():
        try:
            ranges(text)
        except ValueError:
            print(name, 'rejected')
        else:
            raise AssertionError(name)
    reference=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'tmp/b4/verify-off'
    assert check(reference)['status']=='PASS'
    with tempfile.TemporaryDirectory(prefix='b4-check-',dir=ROOT/'tmp') as tmp:
        fixture=Path(tmp)
        for name in ('chip.bin','fast.bin','meta.json','slave.bin'):
            shutil.copyfile(reference/name,fixture/name)
        meta=json.loads((fixture/'meta.json').read_text())
        images={name: (fixture/name).read_bytes() for name in ('chip.bin','fast.bin')}
        # Mutate every opcode/operand byte of every declared optional range.
        tested=0
        for item in ranges(source):
            address=meta['hunk_bases'][item['hunk']]+item['offset']
            name='chip.bin' if address < 0x200000 else 'fast.bin'
            offset=address-(0 if name=='chip.bin' else 0x200000)
            original=images[name]
            for byte in range(item['size']):
                changed=bytearray(original); changed[offset+byte]^=1
                (fixture/name).write_bytes(changed)
                assert check(fixture)['status']=='FAIL',(item,byte)
                tested+=1
            (fixture/name).write_bytes(original)
        print(f'all {tested} hook bytes independently rejected')
        for name,edit in (
            ('nonzero option',dict(custom=[0,0,0,0,1])),
            ('stale source',dict(source_sha256='0'*64)),
            ('wrong layout',dict(hunk_bases=[0]*4))):
            (fixture/'meta.json').write_text(json.dumps(dict(meta,**edit)))
            try:
                check(fixture)
            except ValueError:
                print(name,'rejected')
            else:
                raise AssertionError(name)
        # Actual enabled relay must fail even if its options metadata claims off.
        enabled=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'tmp/b4/verify-on'
        for name in ('chip.bin','fast.bin','meta.json','slave.bin'):
            shutil.copyfile(enabled/name,fixture/name)
        on=json.loads((fixture/'meta.json').read_text());on['custom']=[0]*5
        (fixture/'meta.json').write_text(json.dumps(on))
        assert check(fixture)['status']=='FAIL'
        print('actual enabled relay rejected by byte comparison')
    print('B4 negative checks PASS')


if __name__=='__main__':
    main()
