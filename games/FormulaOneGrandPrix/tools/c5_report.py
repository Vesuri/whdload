#!/usr/bin/env python3
"""Verify saved C5(a) rate evidence; FAIL is an acceptance result, not capture failure."""
import argparse
import hashlib
import json
from pathlib import Path
from c5_capture import decode, evaluate


def report(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    assert meta['status'] == 'CAPTURED' and meta['quit'] == 'OK'
    assert hashlib.sha256((root/'slave.bin').read_bytes()).hexdigest() == meta['build']['slave_sha256']
    result = json.loads((root/'rate.json').read_text())
    assert result == meta['rate']
    samples = []
    for item in result['samples']:
        data = {k: (root/f"{item['name']}-{k}.bin").read_bytes() for k in item['files']}
        assert all(hashlib.sha256(data[k]).hexdigest() == v for k, v in item['files'].items())
        decoded = decode(data['slave'], data['session'], meta['symbols'])
        assert all(item[k] == v for k, v in decoded.items()), item['name']
        samples.append(item)
    checks = evaluate(samples)
    assert all(result[k] == v for k, v in checks.items())
    return dict(checks, evidence_verified=True, build=meta['build'], runtime=meta['runtime'],
                game_inputs=meta['game_inputs'], setup=meta['setup'], effective=meta.get('effective'),
                whd_args=meta['whd_args'], extra_args=meta['extra_args'], route=meta['route'],
                route_reply=meta['route_reply'], hunk_bases=meta['hunk_bases'],
                samples=[dict(name=s['name'], files=s['files']) for s in samples],
                results_png=hashlib.sha256((root/'results.png').read_bytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--repeat')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = report(args.capture)
    if args.repeat:
        assert result == report(args.repeat), 'repeat differs'
        result['exact_repeat'] = 'PASS'
    path = Path(args.out).resolve()
    if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
        raise ValueError('output must stay in project tmp/')
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(f"C5(a) evidence verified; rate {result['rate']:.4f}/s; acceptance {result['status']}")
