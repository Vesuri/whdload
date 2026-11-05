#!/usr/bin/env python3
"""Check saved C4 input evidence; FAIL is an acceptance result, not capture failure."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from c4_capture import evaluate_suite


def report(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    assert meta['status']=='CAPTURED' and meta['quit']=='OK'
    assert hashlib.sha256((root/'slave.bin').read_bytes()).hexdigest()==meta['build']['slave_sha256']
    result = json.loads((root/'input.json').read_text())
    assert result==meta['input']
    symbols=meta['symbols']
    items={}
    for item in result['observations']:
        name=item['name']
        data={suffix:(root/(name+'-'+suffix+'.bin')).read_bytes() for suffix in item['files']}
        assert all(hashlib.sha256(data[s]).hexdigest()==digest for s,digest in item['files'].items())
        raw=item.get('raw',0x4f)
        assert item['key']==data['keys'][raw]
        assert item['masks']==data['h0'][0x18:0x1e].hex()
        assert item['latch']==data['h0'][0x3a915]
        assert item['view']==data['view'].hex() and item['event']==data['view'][10]
        assert item['ticks']==struct.unpack_from('>I',data['slave'],symbols['c2_clock']+24)[0]
        assert item['serial']==struct.unpack_from('>I',data['slave'],symbols['c2_serial'])[0]
        assert item['batch']==struct.unpack_from('>H',data['slave'],symbols['c2_clock']+10)[0]
        assert item['draw_mode']==struct.unpack_from('>H',data['slave'],symbols['c2_draw_mode'])[0]
        assert item['control']==data.get('control',b'').hex()
        if 'buffer' in item:
            buffer=item['buffer']
            assert buffer['deferred']==struct.unpack_from('>I',data['slave'],symbols['c4_deferred'])[0]
            assert buffer['applied']==struct.unpack_from('>I',data['slave'],symbols['c4_applied'])[0]
            assert buffer['live']==struct.unpack_from('>H',data['slave'],symbols['c4_live'])[0]
            assert buffer['state']==data['slave'][symbols['c4_keys']+raw]
        for field,symbol,form in (('mode','c2_mode','>H'),('suspended','c3_suspended','>H'),
                                  ('pauses','c3_pauses','>I')):
            if field in item:
                assert item[field]==struct.unpack_from(form,data['slave'],symbols[symbol])[0]
        items[name]=item
    if result.get('suite'):
        checks=evaluate_suite(items)
        assert checks==result['checks']
        assert result['status']==('PASS' if all(v=='PASS' for v in checks.values()) else 'FAIL')
        return dict(status=result['status'], evidence_verified=True, checks=checks,
                    build=meta['build'],runtime=meta['runtime'],game_inputs=meta['game_inputs'],
                    setup=meta['setup'],effective=meta.get('effective'),whd_args=meta['whd_args'],
                    extra_args=meta['extra_args'],route=meta['route'],route_reply=meta['route_reply'],
                    hunk_bases=meta['hunk_bases'],input=result)
    held=[items[f'held-{n}'] for n in range(5)]
    sampled=[not bool(int(x['masks'],16)&0x2000) for x in held]
    edges=[v and (n==0 or not sampled[n-1]) for n,v in enumerate(sampled)]
    assert sum(edges)==1 and [bool(x['event']&0x20) for x in held]==edges
    assert any(x['draw_mode']==2 for x in held)
    assert [x['ticks'] for x in held]==list(range(held[0]['ticks'],held[0]['ticks']+5))
    assert items['held-irq']['key']==0xb3 and items['release-irq']['key']==0
    assert not items['released']['latch']&0x20
    assert int(items['stick-right']['control'],16)&8 and not int(items['stick-neutral']['control'],16)&8
    assert items['pulse-before']['ticks']==items['pulse-down']['ticks']==items['pulse-up']['ticks']
    assert items['pulse-down']['key']==0xb3
    delivered=bool(not int(items['pulse-scan']['masks'],16)&0x2000 and items['pulse-consumer']['event']&0x20)
    if 'pulse-release' in items:   # buffered build: the release waits for one scan
        up,scan,release,after=(items[n] for n in ('pulse-up','pulse-scan','pulse-release','pulse-after'))
        assert up['key']==0xb3 and up['buffer']['deferred']==items['pulse-down']['buffer']['deferred']+1
        delivered=delivered and bool(release['key']==0 and int(release['masks'],16)&0x2000
            and release['buffer']['applied']==scan['buffer']['applied']+1
            and release['ticks']==scan['ticks']+1
            and not after['event']&0x20 and not after['latch']&0x20)
    else:
        assert items['pulse-up']['key']==0
    assert result['short_pulse']==result['status']==('PASS' if delivered else 'FAIL')
    return dict(status=result['status'], evidence_verified=True,
                build=meta['build'],runtime=meta['runtime'],game_inputs=meta['game_inputs'],
                setup=meta['setup'],whd_args=meta['whd_args'],extra_args=meta['extra_args'],
                route=meta['route'],route_reply=meta['route_reply'],hunk_bases=meta['hunk_bases'],
                input=result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--repeat')
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    result=report(args.capture)
    if args.repeat:
        assert result==report(args.repeat), 'repeat differs'
        result['exact_repeat']='PASS'
    path=Path(args.out).resolve()
    if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
        raise ValueError('output must stay in project tmp/')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print('C4 evidence verified; acceptance '+result['status'])
