#!/usr/bin/env python3
"""Run the native eight-cel death loop with mocked drawing and field interrupts."""
import argparse,json
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE,DATA,STACK,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output
from variants import get


def check(build,variant,model):
 c,sy=machine(build,variant,model);v=get(variant);ocs=variant=='ocs'
 a4=DATA+v.A4_BASE;field=a4+v.A4['field_clock'];abort=a4+(-28796 if ocs else -28820)
 begin,end=(0x19a94,0x19b1a) if ocs else (0x1a7a8,0x1a816)
 state={};rows=[]
 def call(n,regs=None):c.run(SLAVE-CODE+sy[n],registers=regs)
 def advance(n):c.write(field,long((c.get(field,4)+n)&0xffffffff))
 def publish():state['published'].append(c.reg(11));advance(state['gap']);c.return_call()
 def bitmap():
  args=c.read(c.reg(8)+4,14)
  state['draws'].append(args);c.return_call()
 def poll():
  advance(1);c.return_call(1 if state['skip'] and len(state['published'])>=state['skip'] else 0)
 def run(rate,gap,start,skip=0):
  state.clear();state.update(rate=rate,gap=gap,skip=skip,published=[],draws=[])
  c.write(field,long(start));c.write(abort,word(0))
  # Native OCS local surface absent: exercises its fallback bitmap branch.
  frame=0x170000;c.write(frame-40,bytes(44))
  c.run(begin,registers={6:frame})
  return dict(frames=state['published'][:],draws=[x.hex() for x in state['draws']],
              fields=(c.get(field,4)-start)&0xffffffff,aborted=c.get(abort),stack=c.reg(8))
 try:
  c.intercept(CODE+end,lambda:c.return_call())
  c.intercept(CODE+(0x582 if ocs else 0x580),lambda:c.return_call(1))
  c.intercept(CODE+(0xb80 if ocs else 0xc40),publish)
  c.intercept(CODE+(0x2f9a6 if ocs else 0x2efe8),bitmap)
  c.intercept(CODE+(0x322e0 if ocs else 0x31cd6),lambda:c.return_call())
  c.intercept(SLAVE+sy['timing_rate'],lambda:c.return_call(state['rate']))
  c.intercept(SLAVE+sy['modal_input'],poll)
  native=run(50,1,100)
  assert native['frames']==list(range(8)) and native['fields']==8
  call('modal_install',{1:CODE})
  for rate in (50,60):
   for gap in (1,9):
    for start in (100,0xfffffff0):
     got=run(rate,gap,start)
     assert got['frames']==native['frames'] and got['draws']==native['draws'],got
     assert got['stack']==STACK+4
     assert got['fields']==max(8*rate*4//50,8*gap),got
     rows.append(dict(rate=rate,gap=gap,start=start,fields=got['fields']))
   got=run(rate,1,123,3)
   assert got['frames']==[0,1,2] and got['aborted']==1,got
   # Re-entry after a skip must discard the old deadline.
   assert run(rate,1,10000)['fields']==8*rate*4//50
  return dict(model=model,native_fast_control_fields=native['fields'],schedules=rows,abort_and_reentry=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 results=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(passed=True,results=results),indent=2)+'\n')
 print('PASS:',a.variant,'native death cels, timing, wrap, abort and re-entry')
if __name__=='__main__':main()
