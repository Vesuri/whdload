#!/usr/bin/env python3
"""P1 VERIFY restore hashes, excluding display and live interrupt-owned state.

SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS=CUSTOM1=31 python3 tools/presentation_check.py tmp/p1/check.json
Uses VERIFY-only markers; no guest state is altered by this checker.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from route_profile import slave_code, SLAVE, ROUTE
from route_runtime import session, deadline, timeouts, output_path, word, at_breakpoint, delta
from amigaxdev.input import Input

START, END = 0x5350, 0x68000
DISPLAY = [(0x72b2, 0x72b4), (0x72b6, 0x72b8), (0x7ce2, 0x7d26),
           (0x42c00, 0x42c04), (0x52ad0, 0x52b60)]
# The existing write audit's interrupt ranges, not blanket game-data exclusions.
IRQ = [(0x575a, 0x57da), (0x6f2a, 0x6f2c), (0x6f36, 0x6f38),
       (0x6fce, 0x6fd2), (0x7236, 0x7238), (0x727e, 0x7280),
       (0x4b35a, 0x4b366), (0x4b394, 0x4b398), (0x529f2, 0x529f6),
       (0x52b66, 0x52b68), (0x52bf0, 0x52bf1),
       # Startup panel bars and message scroll, called by the field handler.
       (0x53096, 0x5309c), (0x53208, 0x5320e),
       (0x52b7e, 0x52b80), (0x52bb2, 0x52bb4),
       # Field-handler text ticker (Disk.1 $569AE..$56BF8).
       (0x7232, 0x7240), (0x7286, 0x728a), (0x7292, 0x7296),
       (0x52d68, 0x52d74)]


def run(path):
    output = output_path(path)
    code = slave_code(SLAVE)
    markers = [code.find(x) - 4 for x in (b'M3BEFORE', b'M3AFTER!')]
    if min(markers) < 0:
        raise ValueError('requires the VERIFY slave with presentation markers')
    count_offset = code.index(b'M3PUB001') + 8
    boot_timeout, run_timeout = timeouts()
    mask = bytearray(b'\1') * (END - START)
    for a,b in DISPLAY + IRQ:
        mask[a-START:b-START] = bytes(b-a)
    def digest(data):
        return hashlib.sha256(bytes(x if m else 0 for x,m in zip(data,mask))).hexdigest()
    records, inputs = [], []
    with session(boot_timeout) as (g,meta), deadline(run_timeout, 'presentation check'):
        if not hasattr(g,'publication_counter'):
            raise ValueError('P1 option must be enabled')
        base = g.publication_counter - count_offset
        before, after = [base + x for x in markers]
        controls=Input(g, log=inputs.append)
        held=[]; segment=0; boundary=ROUTE[0][0]; total=sum(n for n,_ in ROUTE)
        with tempfile.TemporaryDirectory(prefix='presentation-',dir='tmp') as temp:
            dump=Path(temp)/'image.bin'
            def read():
                dump.unlink(missing_ok=True)
                g.cmd(f'dump binary memory {os.path.relpath(dump)} {START:#x} {END:#x}')
                data=dump.read_bytes()
                if len(data)!=END-START: raise RuntimeError('short dump')
                return data
            # Include the loop head as an exit/input point even if no extra frame fits.
            g.cmd(f'break *{before:#x}'); g.cmd(f'break *{after:#x}')
            g.cmd('break *0x5a2e2')
            saved=None
            while True:
                reply=g.cmd('continue',timeout=run_timeout)
                pc=int(g.cmd('info registers pc').split()[1],16)
                if 'Breakpoint' not in reply: raise RuntimeError(reply)
                field=delta(word(g,0x529f4),meta['anchor_state']['vertb'])
                if pc==before:
                    saved=read()
                elif pc==after:
                    if saved is None: raise RuntimeError('missing before marker')
                    restored=read()
                    changed=[hex(i+START) for i,(a,b,m) in enumerate(zip(saved,restored,mask)) if m and a!=b]
                    records.append(dict(field=field,before_sha256=digest(saved),after_sha256=digest(restored),changed=changed))
                    if changed: break
                    saved=None
                elif pc!=0x5a2e2: raise RuntimeError('unexpected stop')
                if saved is None:
                    if field>=total: break
                    while field>=boundary and segment+1<len(ROUTE):
                        segment+=1; boundary+=ROUTE[segment][0]
                    wanted=ROUTE[segment][1]
                    for event in held:
                        if event not in wanted: controls.button(event,False)
                    for event in wanted:
                        if event not in held: controls.button(event,True)
                    held=wanted[:]
        result=dict(meta,records=records,route=ROUTE,input=inputs,fields=field,
                    input_basis='cumulative fields from entry, at loop/restore boundaries',
                    image_range=[START,END],display_exclusions=DISPLAY,interrupt_exclusions=IRQ,
                    passed=bool(records) and field >= total and saved is None
                    and all(not r['changed'] for r in records))
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(f"{len(records)} presentation restores, passed={result['passed']}")
    if records and records[-1]['changed']: print('changed:',records[-1]['changed'])
    if not result['passed']: raise RuntimeError('presentation restore check failed or no frames exercised')

if __name__=='__main__':
    run(sys.argv[1])
