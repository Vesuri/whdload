#!/usr/bin/env python3
"""Fail-closed phase 2 comparison: all game hunks and every screenshot pixel.
No ignored bytes, tolerated pixels, clock masking or pointer heuristics.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
from cd32_runtime import SIZES


def compare(a,b, prefix=""):
    result_name = prefix+"result.json"
    ma,mb = [json.loads((p/result_name).read_text()) for p in (a,b)]
    for field in ('machine','warp','fsuae_sha256'):
        if ma[field] != mb[field]: raise ValueError('different runtime configuration: '+field)
    if ma['hunks'] != mb['hunks'] or ma['actions'] != mb['actions']:
        raise ValueError('different placements or checkpoint/input routes')
    counts = {}
    for n in range(4):
        x,y = [(p/f'{prefix}h{n}.bin').read_bytes() for p in (a,b)]
        if len(x) != SIZES[n] or len(y) != SIZES[n]: raise ValueError('missing or truncated game hunk')
        offsets = [i for i,(v,w) in enumerate(zip(x,y)) if v != w]
        counts[f'h{n}'] = {'bytes':len(x),'different':len(offsets),'first_offsets':[hex(x) for x in offsets[:20]]}
    x,y = [Image.open(p/('name.png' if prefix else 'menu.png')).convert('RGB') for p in (a,b)]
    if x.size != y.size: raise ValueError('different screenshot dimensions')
    pixels = sum(v != w for v,w in zip(x.get_flattened_data(),y.get_flattened_data()))
    result = {'hunks':counts,'different_pixels':pixels,
              'pass':not pixels and not any(x['different'] for x in counts.values())}
    print(json.dumps(result,indent=2))
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('a',type=Path);p.add_argument('b',type=Path)
    p.add_argument('--name', action='store_true')
    a=p.parse_args()
    raise SystemExit(0 if compare(a.a,a.b,'name-' if a.name else '')['pass'] else 1)
