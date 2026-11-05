#!/usr/bin/env python3
"""Native ejection script differential and PAL/NTSC cinematic clock checks."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import Native,CODE,DATA,STACK,word,long
from ocs_reconstruct import ROOT,new_output
from variants import get
from ejection_source import specification


def check(build,variant,model):
 v=get(variant);s=SLAVE;ocs=variant=='ocs'
 if ocs:c,sy,_,_=setup(build,model)
 else:
  c=Native(ROOT/v.GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],long(CODE))
 field=DATA+v.A4_BASE+v.A4['field_clock'];abort=DATA+v.A4_BASE+(-28796 if ocs else -28820)
 hz='ocs_clock_hz' if ocs else 'timing_hz';clock='ocs_clock_state' if ocs else 'timing_clock'
 state={};rows=[]
 def call(n,regs=None):c.run(s-CODE+sy[n],registers=regs)
 def event(name):
  state[name]+=1;c.return_call()
 def world():event('world')
 def oldworld():state['world']+=1;c.return_call(1)
 def bitmap():
  # Native bitmap arguments: surface.l, x.w, y.w, image.l, frame.w.
  state['poses'].append((c.reg(11),c.get(c.reg(8)+10)))
  c.return_call()
 def start():
  c.write(s+sy[hz],long(state['rate']));c.write(s+sy[clock],long(state['start'])+bytes(20)+word(1)+word(0))
  c.write(s+sy['intro_active'],word(1));c.return_call()
 def finish():
  c.write(field,long(c.get(field,4)+state['gap']))
  if state.get('abort_after') and state['world']>=state['abort_after']:c.write(abort,word(1))
  c.return_call()
 try:
  for off,name in [(0x29d26 if ocs else 0x2acb2,'effect'),(0xb2f4 if ocs else 0xb57e,'explode'),(0x1464c if ocs else 0x148d6,'sound')]:
   c.intercept(CODE+off,lambda name=name:event(name))
  c.intercept(CODE+(0x2f9a6 if ocs else 0x2efe8),bitmap)
  c.intercept(CODE+(0x180c4 if ocs else 0x1898a),lambda:c.return_call())
  c.intercept(CODE+(0x582 if ocs else 0x580),oldworld)
  c.intercept(CODE+(0xb80 if ocs else 0xc40),lambda:c.return_call())
  for _,end in specification(variant):c.intercept(CODE+end,lambda:c.return_call())
  def reset(rate=50,gap=1,startfield=100,abort_after=0):
   state.clear();state.update(rate=rate,gap=gap,start=startfield,world=0,effect=0,explode=0,sound=0,poses=[],samples=[],abort_after=abort_after)
   c.write(field,long(startfield));c.write(abort,word(0))
  initials=[{11:0,12:4,13:199,15:40},{11:0,12:20,13:79,15:40},{11:0,12:20,13:79,15:240}]
  native=[]
  for stage,(off,_) in enumerate(specification(variant)):
   reset();c.run(off,registers=initials[stage])
   native.append(dict(regs=[c.reg(r) for r in (11,12,13,15)],events=[state[k] for k in ('world','effect','explode','sound')]))
  rejects=[]
  c.intercept(s+sy['modal_bad_target'],lambda:(rejects.append(1),c.return_call()))
  for off,_ in specification(variant):
   old=c.read(CODE+off,6)
   for i in range(6):
    bad=bytearray(old);bad[i]^=1;c.write(CODE+off,bytes(bad));call('ejection_guard',{1:CODE})
   c.write(CODE+off,old)
  call('ejection_guard',{1:CODE});assert len(rejects)==18
  call('ejection_install',{1:CODE})
  for name,fn in [('intro_start',start),('intro_world',world),('intro_draw',lambda:c.return_call()),('intro_finish',finish),
                  ('intro_stop',lambda:(c.write(s+sy['intro_active'],word(0)),c.return_call())),('modal_input',lambda:c.return_call())]:c.intercept(s+sy[name],fn)
  for stage in range(2):
   c.intercept(s+sy[f'ejection_draw{stage}'],lambda:state['samples'].append(tuple(c.reg(r) for r in (11,13,15))))
  for rate in (50,60):
   for gap in (1,9):
    for stage in range(3):
     reset(rate,gap,0xfffffff0)
     saved={16:0x1234,3:0x2345,4:0x3456}
     call(f'ejection_entry{stage}',initials[stage]|saved)
     got=dict(regs=[c.reg(r) for r in (11,12,13,15)],events=[state[k] for k in ('world','effect','explode','sound')])
     assert got==native[stage],(stage,got,native[stage])
     assert c.reg(8)==STACK+4 and all(c.reg(r)==n for r,n in saved.items())
     elapsed=(c.get(field,4)-state['start'])&0xffffffff
     ticks=200 if stage==2 else 10
     assert ticks*rate//10<=elapsed<ticks*rate//10+gap,(stage,elapsed)
     assert c.get(s+sy['intro_active'])==0
     if stage<2 and gap==1:
      assert any(x[0]==y[0] and x[1:]!=y[1:] for x,y in zip(state['samples'],state['samples'][1:])),state['samples']
     rows.append(dict(stage=stage,rate=rate,gap=gap,fields=elapsed,events=got['events']))
  # Scripted tumble changes only the private renderer snapshot, not native rates.
  slotaddr=DATA+v.A4_BASE+(-0x478a if ocs else -0x4764)
  for stage in range(3):
   for slot in (0,12,60,61,65535):
    for view,subject in ((10,slot),(10,slot+1),(4,slot),(11,slot)):
     c.write(DATA+v.A4_BASE+(-18318 if ocs else -18280),word(view))
     c.write(DATA+v.A4_BASE+(-18334 if ocs else -18296),word(subject))
     before=bytes(384);c.write(s+sy['timing_scene_angles'],before);c.write(slotaddr,word(slot))
     call('ejection_spin_sample',{16:stage})
     want=bytearray(before)
     if stage==2 and slot<61:
      want[slot*2:slot*2+2]=word(4)
      if view==10 and subject==slot:want[122:124]=word(4)
     assert c.read(s+sy['timing_scene_angles'],384)==bytes(want)
  for stage in range(3):
   reset(abort_after=3);call(f'ejection_entry{stage}',initials[stage])
   assert state['world']==3 and c.get(s+sy['intro_active'])==0
  return dict(model=model,guards=18,native=native,schedules=rows,abort_stages=3)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 results=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,results=results),indent=2)+'\n')
 print('PASS:',a.variant,'ejection native script, cadence, samples, abort and guards')
if __name__=='__main__':main()
