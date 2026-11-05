#!/usr/bin/env python3
"""Known-duration intervals and deliberate accounting/budget failures."""
from types import SimpleNamespace
from check_simulation_budget import measure
class Fixture:
 def __init__(self,work_fields=1):
  self.fields=[];self.rows={};regs=[0]*17;regs[13]=0x2000
  for i in range(10):
   for j in range(work_fields+1):
    n=len(self.fields);self.fields.append(SimpleNamespace(index=n,cycles=1000))
    pc=0x198 if j==0 else 0x16a if j==work_fields else 0x100
    self.rows[n]=[(pc,1000,regs)]
 def instructions(self,f):return iter(self.rows[f.index])
r=measure(Fixture(),0,0x2000,2)
assert r['complete_iterations']==10 and r['max_period_percent']==50
for name,t in [('overrun',Fixture(3)),('cycle accounting',Fixture())]:
 if name=='cycle accounting':t.fields[-1].cycles+=10000
 try:measure(t,0,0x2000,2)
 except AssertionError:pass
 else:raise AssertionError('accepted '+name)
print('PASS: exact 50% budget, rejected overrun and corrupt cycle accounting')
