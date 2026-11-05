"""Validate a task-owned, hash-checked VERIFY ceiling build before booting it."""
import hashlib
import json
from pathlib import Path
from cd32_runtime import ROOT


def load(path):
    target = (ROOT/path).resolve()
    if (ROOT/'tmp').resolve() not in target.parents:
        raise ValueError('ceiling slave must stay in tmp/')
    fixture = json.loads((target.parent/'build.json').read_text())
    arm = fixture.get('ceiling')
    if not fixture.get('verify_only') or arm not in ('control','c2p','drawing-control','drawing','drawing-bitmap','drawing-clear'):
        raise ValueError('verified ceiling fixture required')
    data = target.read_bytes()
    if hashlib.sha256(data).hexdigest() != fixture['sha256'] or len(data) != fixture['bytes']:
        raise ValueError('ceiling fixture hash/size mismatch')
    if arm.startswith('drawing'):
        if len(data) != 7836 or fixture.get('drawing_entries') != [0x2efe8,0x31cd6]:
            raise ValueError('unexpected drawing fixture layout')
        if fixture.get('drawing_word') != 0x1e74 or fixture.get('drawing_installs') != 0x1e70:
            raise ValueError('unexpected drawing marker layout')
        words=('4e75' if arm in ('drawing','drawing-bitmap') else '48e7')+('4e75' if arm in ('drawing','drawing-clear') else '48e7')
        if data[32+fixture['drawing_word']:36+fixture['drawing_word']] != bytes.fromhex(words):
            raise ValueError('drawing patch word disagrees with arm')
    elif len(data) != 7728:
        raise ValueError('unexpected converter fixture size')
    return target, fixture
