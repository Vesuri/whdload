#!/usr/bin/env python3
"""Check every observed PC against installed patch interiors, regardless of origin.

This complements register-derived indirect targets and stack-return checks.
External code and exception returns are not filtered out. Missing-PC records
remain explicit gaps; this checks observed destinations, not unobserved paths
or exception-frame/stack semantics.
"""
import argparse
import collections
import json
import re
from pathlib import Path
import audit_hooks
import _amigaxdev  # noqa: F401
from amigaxdev import barto


def observed_entries(pcs, code, interiors, padding):
    counts=collections.Counter();missing=0;observed=0
    for pc in pcs:
        if pc is None or pc==0x7fffffff:
            missing+=1
            continue
        observed+=1
        offset=pc-code
        assert offset not in interiors or offset in padding, f'observed native patch-interior PC {offset:#x}'
        if offset in padding:counts[hex(offset)]+=1
    assert observed, 'no instruction PCs in trace'
    return dict(observed_instruction_pcs=observed,missing_pc_records=missing,
                declared_padding=dict(counts))


def inspect(folder, listing, trace=None):
    folder=Path(folder)
    installation=audit_hooks.installed(folder,listing)
    audit=audit_hooks.audit(listing)
    interiors=set();padding=set()
    for group in audit['ranges']:
        start,end=int(group['start'],16),int(group['end'],16)
        entries={p['start'] for p in group['patches'] if p['command']!='NOP'}|{start}
        interiors.update(set(range(start,end))-entries)
        for p in group['patches']:
            if p['command']=='NOP':padding.update(range(p['start'],p['end'],2))
            elif p['command']=='PSS':padding.update(range(p['start']+6,p['end'],2))
            elif p['command']=='L' and p['argument']=='c1c14e71':
                # The flat-motion replacement is two native instructions:
                # MULS.W D1,D0 followed by NOP, not a four-byte instruction.
                padding.add(p['start']+2)
    meta={k:int(v,0) for k,v in re.findall(r'^(code|base)=(\S+)',(folder/'anchor.txt').read_text(),re.M)}
    memory=(folder/'code.bin').read_bytes()
    for offset in padding:
        at=meta['code']-meta['base']+offset
        assert memory[at:at+2]==bytes.fromhex('4e71'), 'declared padding is not installed NOP'
    trace=trace or barto.load(folder/'trace.bin')
    result=observed_entries((pc for f in trace.fields for pc,_,_ in trace.instructions(f)),meta['code'],interiors,padding)
    result.update(installation=installation,scope=__doc__.strip())
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path)
    p.add_argument('--listing',type=Path,required=True);a=p.parse_args()
    print(json.dumps(inspect(a.capture,a.listing),indent=2))
