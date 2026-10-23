#!/usr/bin/env python3
"""Adversarial B4 checks against actual off/on captures; all fixtures stay in tmp/."""
import json
import shutil
import tempfile
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
        'empty inventory':source.replace(declaration,'').replace('        PL_PS $3c9d2,verify_pacer',''),
    }
    for name,text in bad_sources.items():
        try:
            ranges(text)
        except ValueError:
            print(name, 'rejected')
        else:
            raise AssertionError(name)
    reference=ROOT/'tmp/b4/verify-off'
    assert check(reference)['status']=='PASS'
    with tempfile.TemporaryDirectory(prefix='b4-check-',dir=ROOT/'tmp') as tmp:
        fixture=Path(tmp)
        for name in ('chip.bin','fast.bin','meta.json','slave.bin'):
            shutil.copyfile(reference/name,fixture/name)
        meta=json.loads((fixture/'meta.json').read_text())
        fast=(fixture/'fast.bin').read_bytes()
        offset=meta['hunk_bases'][0]-0x200000+0x3c9d2
        # Mutate every opcode/operand byte separately, including relocated bytes.
        for byte in range(6):
            changed=bytearray(fast); changed[offset+byte]^=1
            (fixture/'fast.bin').write_bytes(changed)
            assert check(fixture)['status']=='FAIL',byte
        print('all six hook bytes independently rejected')
        (fixture/'fast.bin').write_bytes(fast)
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
        enabled=ROOT/'tmp/b4/verify-on'
        for name in ('chip.bin','fast.bin','meta.json','slave.bin'):
            shutil.copyfile(enabled/name,fixture/name)
        on=json.loads((fixture/'meta.json').read_text());on['custom']=[0]*5
        (fixture/'meta.json').write_text(json.dumps(on))
        assert check(fixture)['status']=='FAIL'
        print('actual enabled relay rejected by byte comparison')
    print('B4 negative checks PASS')


if __name__=='__main__':
    main()
