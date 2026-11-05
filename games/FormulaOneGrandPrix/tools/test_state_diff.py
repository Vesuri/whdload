#!/usr/bin/env python3
"""Adversarial A3 report checks using local, derived evidence, never tracked fixtures.
Usage: test_state_diff.py tmp/a3/probe3
"""
import contextlib
import gzip
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from state_diff import scratch, report, digest, changed_offsets

# Exercise block boundaries and a short final block against an independent oracle.
a=bytes(12301);b=bytearray(a)
for n in (0,1,4095,4096,8191,8192,12300):b[n]=1
assert list(changed_offsets(a,b))==[n for n,(x,y) in enumerate(zip(a,b)) if x!=y]
source=scratch(sys.argv[1])
with tempfile.TemporaryDirectory(prefix='state-test-',dir=source.parent) as temp:
    target=Path(temp)
    original_meta=json.loads((source/'meta.json').read_text())
    original_events=(source/'events.jsonl').read_text()
    for name in ('fast.bin','chip.bin'):
        shutil.copyfile(source/name,target/name)
    for item in source.glob('*.bin.gz'):
        shutil.copyfile(item,target/item.name)
    def reset():
        (target/'meta.json').write_text(json.dumps(original_meta))
        (target/'events.jsonl').write_text(original_events)
    def run():
        with contextlib.redirect_stdout(io.StringIO()):
            return report(target)
    def reject(label):
        try:run()
        except (ValueError,KeyError):return
        raise AssertionError('accepted '+label)
    reset()
    assert run()['status']=='CLASSIFIED'
    meta=dict(original_meta,status='FAILED');(target/'meta.json').write_text(json.dumps(meta))
    reject('failed capture')
    reset();meta=dict(original_meta,screens=[[0,0x1000000]])
    (target/'meta.json').write_text(json.dumps(meta));reject('forged screen exclusion')
    reset();(target/'events.jsonl').write_text('\n'.join(original_events.splitlines()[:-1])+'\n')
    reject('missing return snapshot')
    reset();meta=dict(original_meta,frames=original_meta['frames']+1)
    (target/'meta.json').write_text(json.dumps(meta));reject('missing complete frame')
    reset();events=[json.loads(x) for x in original_events.splitlines()]
    events[0]['sha256']='0'*64
    (target/'events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events));reject('corrupt snapshot')
    reset();events=[json.loads(x) for x in original_events.splitlines()]
    e=next(x for x in events if x['site']==0x3c9ba and x['edge']=='after')
    data=bytearray(gzip.decompress((target/e['file']).read_bytes()));data[0x10000]^=1
    (target/e['file']).write_bytes(gzip.compress(data));e['sha256']=digest(data)
    (target/'events.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in events))
    changed=run()
    assert changed['status']=='UNCLASSIFIED'
    assert [str(0x3c9ba),0,0x10000] in changed['unclassified']
    print('A3 negative checks PASS: failed/short/odd/corrupt captures and an unknown renderer byte rejected')
