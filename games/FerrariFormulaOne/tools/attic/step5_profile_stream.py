"""Exclude only repeated pacing polls, retaining the final successful poll.
The old all-car diagnostic stayed in debt and never idled. Plan B can keep pace.
"""
import re
from amigaxdev import barto
def instructions(trace,listing,probe):
 m=re.search(r'C1Head:\n(.*?)C1Vbl:',listing,re.S) if 'C1Head:' in listing else re.search(r'schedule_begin:\n(.*?)schedule_end:',listing,re.S)
 wait=int(re.search(r'^00:([0-9A-F]+).*bsr.w FF1TimeDue',m[1],re.M)[1],16)+probe
 loop=[]
 def filtered():
  polls=[i for i,x in enumerate(loop) if x[0]==wait]
  if len(polls)>1:return loop[:polls[0]]+loop[polls[-1]:]
  return loop
 for f in trace.fields:
  for ins in trace.instructions(f):
   if ins[0]==0x65174:
    yield from filtered();loop=[]
   loop.append(ins)
 yield from filtered()
def fields(trace,listing,probe):
 class View:
  fields=[None]
  def instructions(self,field):return instructions(trace,listing,probe)
 return View()
