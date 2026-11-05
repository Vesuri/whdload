#!/usr/bin/env python3
"""Deliberate failures prove the phase-7 checkers reject bad evidence."""
import copy,json,struct,subprocess,sys
from harness import ROOT
from audit_simulation import ranges,originals,validate
from check_units import check as units,MARK
from check_disabled import check as installed
p=ROOT/'tmp/phase7/final-straight-a500';raw=(p/'code.bin').read_bytes();rs=ranges();bs=originals();results=[]
def rejects(name,fn):
 try:fn()
 except AssertionError as e:results.append(dict(test=name,rejected=True,reason=str(e)))
 else:raise AssertionError('checker accepted sabotage: '+name)
units(raw);installed(p);validate(rs,bs)
at=(raw.index(MARK)+len(MARK)+1)&~1
bad=bytearray(raw);struct.pack_into('>I',bad,at+4,0)
rejects('unexecuted assertion runner',lambda:units(bad))
bad2=bytearray(raw);struct.pack_into('>I',bad2,at,1);struct.pack_into('>I',bad2,at+8,1)
rejects('assembly failure',lambda:units(bad2))
rejects('overlapping hook',lambda:validate(rs+[rs[0]],bs))
bad3={**bs,'h4':bytearray(bs['h4'])};bad3['h4'][0xa000:0xa006]=bytes.fromhex('4ef9000000f8')
rejects('incoming branch into displaced instruction',lambda:validate(rs,bad3))
meta=json.loads((p/'capture.json').read_text());chip=bytearray((p/'chip.bin').read_bytes());chip[meta['regions']['h4']+0x130c]^=1
rejects('wrong installed hook byte',lambda:installed(p,chip))
oracle=ROOT/'tools/verify_state.py'
self_check=subprocess.run([sys.executable,str(oracle),str(p),str(p),'--expect-equal'],capture_output=True,text=True)
assert self_check.returncode==0,self_check.stderr
different=subprocess.run([sys.executable,str(oracle),str(p),str(ROOT/'tmp/phase7/final-straight-a1200'),'--expect-equal'],capture_output=True,text=True)
assert different.returncode!=0 and 'core state differs' in different.stderr
results.append(dict(test='original cross-CPU state inequality',rejected=True,reason='core-state equality gate rejects original drawing dependency'))
print(json.dumps(dict(status='PASS',negative_controls=results),indent=2))
