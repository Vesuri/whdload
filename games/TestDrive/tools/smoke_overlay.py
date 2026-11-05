#!/usr/bin/env python3
"""Probe both live overlay exits; no target-memory writes. Run after td.py serve."""
import sys
from pathlib import Path
from td import server
out=Path(__file__).resolve().parents[1]/'tmp/build/overlay-smoke.txt'
log=[]
def call(s):
    r=server.request(s); log.append(s+'\n'+r); out.write_text('\n'.join(log)); print(r,flush=True); return r
# Hunk and slave addresses are specific to this calibrated a1200-040 boot.
# Assert installed jumps before using them; never silently reuse on another layout.
call('stop')
for addr,target in [(0x9e3b00,0x9fd5fe),(0x9e4086,0x9fd608)]:
    r=call(f'gdb x/i {addr:#x}')
    assert f'jmp {target:#x}' in r, r
for target,regs in [(0x9fd5fe,['a2','a3','a6']),(0x9fd608,['d0','d1','d2','a0','a1','a2','a3','a4'])]:
    call(f'until {target:#x}')
    n=len(regs)
    lines=['set $entrysp = $sp']
    for i,reg in enumerate(regs): lines.append(f'set $saved_{reg} = *(unsigned int*)($sp+{4*i})')
    lines += [f'set $returnpc = *(unsigned int*)($sp+{4*n})','x/6i $pc','x/3i 0x9fd416']
    call('gdb '+'\n'.join(lines))
    call(f'until {target+4:#x}') # flush has returned, before the displaced movem
    call('gdb stepi\nstepi')
    conditions=[f'${reg} == $saved_{reg}' for reg in regs]+[f'$sp == $entrysp+{4*(n+1)}','$pc == $returnpc']
    r=call('gdb printf "RESTORE_OK=%d\\n", ('+' && '.join(conditions)+')')
    assert 'RESTORE_OK=1' in r, r
call('cont')
print('PASS: both hooks, cache-flush return, displaced register restore and return stack verified.')
