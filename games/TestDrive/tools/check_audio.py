#!/usr/bin/env python3
"""Match sample starts to their IRQs; a one-shot needs initial and end IRQs."""
import json,re,sys
from pathlib import Path
from harness import ROOT

def check(name,require_fixed=False):
 out=ROOT/'tmp/audio'/name;pending={};samples=[];negative=0
 for line in (out/'events.txt').read_text().splitlines():
  a=line.split()
  if not a:continue
  if a[0]=='START':
   f=int(a[1]);beam=int(a[2],16);mask=int(a[3],16)&15;ptr=int(a[4],16)
   assert mask in (1,2,4,8)
   item=dict(field=f,beam=beam,mask=mask,ptr=ptr,words=int(a[5]),repeat=int(a[6]),irqs=[])
   samples.append(item);pending[mask]=item
  elif a[0]=='IRQ':
   f=int(a[1]);mask=int(a[4],16)&15;n=int(a[5]);ptr=int(a[6],16)
   negative+=n<0
   if mask in pending and ptr==pending[mask]['ptr']:
    pending[mask]['irqs'].append(dict(field=f,beam=int(a[2],16),count=n))
    if n==0:del pending[mask]
 complete=[x for x in samples if x['irqs'] and x['irqs'][-1]['count']==0]
 late=[x['field'] for x in complete if x['irqs'][0]['field']-x['field']>1]
 if require_fixed:
  assert complete
  assert all([v['count'] for v in x['irqs']]==[1] for x in samples if x not in complete)
  assert negative==0 and not late
  assert all([v['count'] for v in x['irqs']]==[1,0] for x in complete)
 result=dict(name=name,samples=len(samples),complete=len(complete),negative_count_irqs=negative,missed_initial_irq_start_fields=late,checks='PASS' if require_fixed else 'before-fix evidence',details=complete)
 (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='details'}))
 return result
if __name__=='__main__':
 for arg in sys.argv[1:]:check(arg, arg.startswith('fixed'))
