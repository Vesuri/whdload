#!/usr/bin/env python3
"""Verify the shared build inputs. --record is only for an intentional toolchain update."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    h = hashlib.sha256()
    for p in sorted(x for x in path.rglob('*') if x.is_file()):
        h.update(p.relative_to(path).as_posix().encode()+b'\0')
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

paths = {'VASM': Path(os.environ['VASM']), 'NDK': Path(os.environ['NDK']),
         'NDK_ASM': Path(os.environ['NDK_ASM']),
         'WHDLOAD/Include': Path(os.environ['WHDLOAD'])/'Include',
         'WHDLOAD/Src/sources/whdload': Path(os.environ['WHDLOAD'])/'Src/sources/whdload'}
pin = ROOT/'manifest/slave-toolchain.json'
actual = {name: digest(path) for name,path in paths.items()}
if sys.argv[1:] == ['--record']:
    pin.write_text(json.dumps(actual, indent=2)+'\n')
else:
    expected = json.loads(pin.read_text())
    if actual != expected:
        sys.exit('Shared toolchain differs from manifest/slave-toolchain.json; build refused')
    print('Shared assembler, NDK and WHDLoad source hashes verified')
