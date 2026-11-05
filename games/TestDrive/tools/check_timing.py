#!/usr/bin/env python3
"""Check counted PAL quanta against each observed, nonblocking simulation step.

This gate deliberately rejects event/stage transitions. Separate event captures
must prove penalty, acknowledgement, recovery and blocking intervals.
"""
import argparse,json
from pathlib import Path

def results(count,total,stage):
 # h4:$366/$38E and $C60: count/12, speed sum/count, stage score.
 delta=count-[700,1100,1200,1100,1500][stage]
 return dict(seconds=count//12,average=total//count,
             score=(stage+4)*1000000//max(delta,100)+100*max(100-delta,0))

def check(path):
 samples=json.loads((path/'states/samples.json').read_text())
 assert samples and len({x['period'] for x in samples})==1
 p=samples[0]['period'];assert p in (2,5)
 assert all(b['vbl']==a['vbl']+1 for a,b in zip(samples,samples[1:]))
 assert len({x['stage'] for x in samples})==1,'separate stage transition fixture required'
 assert all(x['event']==0 and x['chances']==5 for x in samples),'separate event fixture required'
 count_num=0;sum_num=0;previous=None;steps=0;counted=0
 for i,s in enumerate(samples):
  tick=s['deadline']
  if tick!=previous:
   if previous is not None:assert tick-previous==p,('overrun',i,tick-previous,p)
   previous=tick;steps+=1
   frame=(path/f'states/frame-{i:04d}.bin').read_bytes()
   latched=int.from_bytes(frame[:2],'big')
   if latched:
    counted+=1;count_num+=6*p;sum_num+=(s['speed']>>16)*6*p
  assert s['samples']==1+count_num//25,('clock',i,s['samples'],1+count_num//25)
  assert s['sum_speed']==sum_num//25,('speed integral',i,s['sum_speed'],sum_num//25)
 final=samples[-1];display=results(final['samples'],final['sum_speed'],final['stage'])
 return dict(status='PASS',period=p,observed_fields=len(samples),steps=steps,
             counted_fields=counted*p,count_units=final['samples']-1,
             count_remainder=count_num%25,speed_sum=final['sum_speed'],
             results_model=display,
             scope='Nonblocking first-stage tape; results formula checked from state, not a captured results screen')

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('captures',nargs='+',type=Path)
 args=ap.parse_args();print(json.dumps({p.name:check(p) for p in args.captures},indent=2))
