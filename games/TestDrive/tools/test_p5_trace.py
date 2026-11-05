#!/usr/bin/env python3
"""Reject changed native return values/registers without altering capture files."""
import json,re
from harness import ROOT
import check_p5_trace as c
from check_units import MARK
p=ROOT/'tmp/phase8/grip-budget-a500';m=json.loads((p/'capture.json').read_text());raw=(p/'trace-start/code.bin').read_bytes()
syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
at=raw.index(MARK)+len(MARK);at=(at+1)&~1;slave=m['base']+at-syms['verify_unit_results'];ret=slave+syms['sim_relax_word']-2
assert raw[ret-m['base']:ret-m['base']+2]==b'\x4e\x75'
original_load=c.barto.load
for register in [0,1]:
 def changed_load(path):
  t=original_load(path);original_instructions=t.instructions
  def changed_instructions(f):
   for pc,cost,r in original_instructions(f):
    if pc==ret:r=list(r);r[register]^=1
    yield pc,cost,r
  t.instructions=changed_instructions
  return t
 c.barto.load=changed_load
 try:c.check(p)
 except AssertionError:pass
 else:raise AssertionError('accepted corrupted register '+str(register))
 c.barto.load=original_load
print('PASS: rejected wrong distance result and preserved-register clobber')
