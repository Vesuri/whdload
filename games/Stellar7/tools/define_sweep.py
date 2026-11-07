#!/usr/bin/env python3
"""Diagnostic exclusion (open-work step 9): rebuild each release variant with every
conditional symbol in src/ (except VERIFY) set to 0 and to 1, and record which settings
change the release bytes, which leave them unchanged and which the source refuses.
Every changing symbol must be a production switch with its default in sim60.s,
motion60.s or sort60.s (docs/development.md lists them).
Usage: tools/define_sweep.py OUT.json   (OUT under tmp/)"""
import hashlib, json, os, re, subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
os.chdir(root)
out = Path(sys.argv[1]).resolve()
out.relative_to(root/'tmp')
VARIANTS = ('Stellar7', 'Stellar7-Sim60', 'Stellar7-Sim68000')
symbols = sorted({m[1] for p in Path('src').glob('*.s')
                  for m in re.finditer(r'^\s*(?:IFD|IFND|IFNE|IFEQ|IFGT|IFLT|IFGE|IFLE)\s+([A-Z_0-9]+)',
                                       p.read_text(encoding='latin1'), re.M)} - {'VERIFY'})

def build(variant, extra=''):
    env = {k: v for k, v in os.environ.items() if k not in ('VASM_EXTRA', 'SIM68000_SUBSTEPS', 'VERIFY_FLAGS')}
    env.update(VARIANT=variant, VASM_EXTRA=extra)
    r = subprocess.run(['make', '-s', 'build', 'BUILD=release'], env=env, capture_output=True, text=True)
    if r.returncode:
        return None, (r.stdout+r.stderr).strip().splitlines()[-3:]
    return hashlib.sha256(Path(f'tmp/build/release/{variant}.Slave').read_bytes()).hexdigest(), None

release = {v: build(v)[0] for v in VARIANTS}
result = dict(release=release, symbols={})
for s in symbols:
    row = {}
    for v in VARIANTS:
        for value in ('0', '1'):
            sha, error = build(v, f'-D{s}={value}')
            row[f'{v}={value}'] = 'same' if sha == release[v] else ('error: '+' | '.join(error) if error else 'changed')
    result['symbols'][s] = row
    print(s, ' '.join(f'{k}:{x[:7]}' for k, x in row.items()), flush=True)
for v in VARIANTS:
    assert build(v)[0] == release[v]
Path(out).write_text(json.dumps(result, indent=2)+'\n')
print('changing:', ' '.join(s for s, row in result['symbols'].items() if 'changed' in row.values()), flush=True)
