#!/usr/bin/env python3
"""Acceptance checks against retained phase-1 emulator captures."""
import json,sys,tempfile,shutil
from pathlib import Path
from harness import ROOT
from state_report import read,value,VARIABLES,DATA_SIZE
from compare_state import compare
from td_report import regions
from task_state import inspect
from ingame import driving
p=ROOT/'tmp/phase1'
a=p/'final-a/state';b=p/'final-b/state';later=p/'rebuilt-later/state'
assert not any(compare(a,b,raw=True).values()), 'same-window fresh boots differ'
for name in ('final-a','final-b','a1200-verified','a1200-030-verified'):
    m,data=read(p/name/'state');assert m['vbl_first']==600
assert 'VBL_INCREMENT_OK=1' in (p/'shipped-title/state/watchpoints.txt').read_text()
assert '[1, 1, 1, 1, 1, 1, 1, 1]' in (p/'shipped-title/frames.txt').read_text()
_,aa=read(a);_,ll=read(later)
assert len(aa)==len(ll) and all(x!=y for x,y in zip(aa,ll)), 'different scenes falsely compare equal'
# A shifted semantic field must be detected, even when sample counts and metadata match.
with tempfile.TemporaryDirectory(dir=ROOT/'tmp',prefix='compare-negative-') as tmp:
 d=Path(tmp)/'state';shutil.copytree(a,d)
 f=d/'0000.bin';raw=bytearray(f.read_bytes());raw[0x7ffe+VARIABLES['selection_a81c'][0]]^=1;f.write_bytes(raw)
 assert compare(a,d)['selection_a81c']==[0]
 f.unlink()
 try:compare(a,d)
 except ValueError:pass
 else:raise AssertionError('missing sample accepted')
rr={n:(lo,hi) for lo,hi,n,o in regions((p/'shipped-a500/code.bin').read_bytes(),0xc00000)}
assert rr['td'][1]-rr['td'][0]==0x7c0c and rr['td-data'][1]-rr['td-data'][0]==DATA_SIZE
assert len(inspect(p/'shipped-a500/code.bin',0xc00000,p/'shipped-a500/chip.bin'))==2
assert driving(p/'shipped-a500/title.png')
assert driving(ROOT/'tmp/build/fixed-startup.png')
assert not driving(ROOT/'tmp/build/baseline-startup.png')
assert not driving(ROOT/'tmp/build/baseline-attract.png')
assert not driving(p/'rebuilt-a/end.png')
assert not driving(p/'rebuilt-later/end.png')
import _amigaxdev
from amigaxdev import barto
t=barto.load(str(p/'shipped-a500/trace.bin'))
pcs=[pc for f in t.fields for pc,c,r in t.instructions(f) if pc not in (None,0x7fffffff)]
assert len(t.fields)==3 and pcs
assert any(rr['td'][0]<=pc<rr['td'][1] for pc in pcs)
print('PASS: regions/BPTR chain, Exec tasks, trace PCs, two driving/four non-driving fixtures, fresh-boot raw equality, different-scene inequality, semantic mutation and missing-sample rejection')
