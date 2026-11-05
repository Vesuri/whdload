#!/usr/bin/env python3
"""Recompute A3 evidence checks; never promote missing or partial captures.
Usage: state_gate.py tmp/a3
"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
from state_diff import scratch, report, digest
from race_profile import GAME


def check(root):
    root=scratch(root)
    result=dict(status='INCOMPLETE')
    target=root/'acceptance.json'
    target.write_text(json.dumps(result)+'\n')
    cases={}
    hashes=set()
    for name in ('green','tow','follow','qualifying','replay'):
        meta=json.loads((root/name/'meta.json').read_text())
        if meta['frames']!=50 or meta['mode']!=('replay' if name=='replay' else 'live'):
            raise ValueError(name+': expected 50 complete frames in the intended loop')
        if meta['whd_args']!='CUSTOM1=0 CUSTOM2=0 CUSTOM3=0 CUSTOM4=0 CUSTOM5=0':
            raise ValueError('capture options are not all off')
        hashes.add(meta['slave_sha256'])
        with contextlib.redirect_stdout(io.StringIO()):
            analysis=report(root/name)
        if analysis['status']!='CLASSIFIED':
            raise ValueError(name+': unclassified changed bytes')
        draw=analysis['calls'][str(0x3cce8 if name=='replay' else 0x3c9ba)]
        cases[name]=dict(frames=50,draw_calls=draw['calls'],classes=draw['classes'],
                         changed_bytes=draw['changed_bytes'])
    if len(hashes)!=1:
        raise ValueError('captures mix slave builds')
    subprocess.run([sys.executable,str(Path(__file__).with_name('state_audit.py')),
                    str(root/'static-audit.json')],check=True,stdout=subprocess.DEVNULL)
    static=json.loads((root/'static-audit.json').read_text())
    if static['status']!='CLASSIFIED' or static['game_sha256']!=digest(Path(GAME).read_bytes()):
        raise ValueError('static renderer write audit failed')
    sources=json.loads((root/'access-sources.json').read_text())
    if set(sources)!={'green','tow','follow','practice','replay'}:
        raise ValueError('missing auxiliary instruction evidence')
    static_pcs={w['pc'] for w in static['writes']}
    trace_checks={}
    for name,(trace,fast) in sources.items():
        inventory=json.loads((root/(name+'-access.json')).read_text())
        if inventory['unknown'] or inventory['trace_sha256']!=digest(scratch(trace).read_bytes()) or inventory['fast_sha256']!=digest(scratch(fast).read_bytes()):
            raise ValueError(name+': stale or unresolved instruction inventory')
        writers={item['pc'] for item in inventory['accesses'] if item['access']=='write' and item['call'] in ('h0+3c9ba','h0+3cce8')}
        if not writers or writers-static_pcs:
            raise ValueError(name+': renderer writer missing from static audit: '+str(writers-static_pcs))
        trace_checks[name]=dict(renderer_store_pcs=len(writers),unresolved=0)
    subprocess.run([sys.executable,str(Path(__file__).with_name('test_state_diff.py')),
                    str(root/'probe3')],check=True,stdout=subprocess.DEVNULL)
    result=dict(status='PASS',cases=cases,trace_checks=trace_checks,negative_checks=True,static_write_instructions=static['write_instructions'],
                static_classes=static['classes'],slave_sha256=hashes.pop(),
                scope='Pinned game: 50 frames per sample plus static renderer store audit. No simulation or performance change; no equivalence claim.')
    target.write_text(json.dumps(result,indent=2)+'\n')
    print('A3 PASS: five 50-frame samples; all renderer stores and changed bytes classified')
    return result


if __name__=='__main__':
    check(sys.argv[1])
