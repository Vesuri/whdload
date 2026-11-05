#!/usr/bin/env python3
"""Waypoint fly-by scheduler, camera arguments, hook and return contracts."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import Native,CODE,DATA,STACK,word,long
from ocs_reconstruct import ROOT,new_output
from variants import get
from autopilot_source import site


def check(build,variant,model):
 v=get(variant);s=SLAVE
 if variant=='ocs':c,sy,_,_=setup(build,model)
 else:
  c=Native(ROOT/v.GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],long(CODE))
 def call(n,regs=None):c.run(s-CODE+sy[n],registers=regs)
 field=DATA+v.A4_BASE+v.A4['field_clock']
 hz='ocs_clock_hz' if variant=='ocs' else 'timing_hz'
 clock='ocs_clock_state' if variant=='ocs' else 'timing_clock'
 state={};rows=[]
 try:
  rejects=[]
  c.intercept(s+sy['modal_bad_target'],lambda:(rejects.append(1),c.return_call()))
  off=site(variant);old=c.read(CODE+off,6)
  for i in range(6):
   bad=bytearray(old);bad[i]^=1;c.write(CODE+off,bytes(bad))
   call('autopilot_guard',{1:CODE})
  c.write(CODE+off,old);call('autopilot_guard',{1:CODE});assert len(rejects)==6
  call('modal_install',{1:CODE})
  assert c.read(CODE+off,6)==struct.pack('>HI',0x4ef9,s+sy['autopilot_entry'])
  def start():
   c.write(s+sy[hz],long(state['rate']))
   c.write(s+sy[clock],long(state['start'])+bytes(20)+word(1)+word(0))
   c.write(s+sy['intro_active'],word(1));c.return_call()
  def world():state['ticks']+=1;c.return_call()
  def draw():
   assert c.get(s+sy['intro_active'])==1
   state['samples'].append((state['ticks'],c.get(s+sy[clock]+4,4)))
   c.return_call()
  def finish():c.write(field,long(c.get(field,4)+state['gap']));c.return_call()
  def camera():
   assert c.read(c.reg(8)+4,4)==struct.pack('>HH',12,0)
   state['cameras']+=1;c.return_call()
  for name,fn in [('intro_start',start),('intro_world',world),('intro_draw',draw),
                  ('intro_finish',finish),('intro_stop',lambda:(c.write(s+sy['intro_active'],word(0)),c.return_call())),
                  ('autopilot_camera',camera),('autopilot_overlay',lambda:c.return_call())]:c.intercept(s+sy[name],fn)
  for rate in (50,60):
   for gap in (1,3,9):
    for startfield in (100,0xfffffff0):
     state.update(rate=rate,gap=gap,start=startfield,ticks=0,cameras=0,samples=[])
     c.write(field,long(startfield))
     saved={r:0x120000+r*123 for r in (3,4,11,12,13,14,15,16)}
     c.run(s-CODE+sy['autopilot_scene'],args=struct.pack('>HHH',12,0,240),registers=saved)
     assert all(c.reg(r)==value for r,value in saved.items()),'callee-saved registers'
     assert c.reg(8)==STACK+4,'unbalanced scene stack'
     elapsed=(c.get(field,4)-startfield)&0xffffffff
     assert 240<=elapsed<240+gap,(state,elapsed)
     assert state['ticks']==elapsed*10//rate,(rate,gap,state['ticks'],elapsed)
     assert state['cameras']==1 and c.get(s+sy['intro_active'])==0
     if gap<rate//10:assert any(t==u and f!=g for (t,f),(u,g) in zip(state['samples'],state['samples'][1:])),state
     rows.append(dict(hz=rate,gap=gap,wrap=startfield>100,ticks=state['ticks'],pictures=len(state['samples'])))
  return dict(model=model,guards=6,schedules=rows)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 results=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,results=results),indent=2)+'\n')
 print('PASS:',a.variant,'autopilot clock, arguments, wrap and guards')
if __name__=='__main__':main()
