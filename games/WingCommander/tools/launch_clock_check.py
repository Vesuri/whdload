#!/usr/bin/env python3
"""Launch clocks, native script trajectories and fractional projection contracts."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_reconstruct import ROOT,new_output
from variants import get
from launch_source import specification


def check(build,variant,model):
 v=get(variant);s=SLAVE;code=CODE;data=DATA
 if variant=='ocs':c,sy,_,_=setup(build,model)
 else:
  c=Native(ROOT/v.GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],long(code))
 def call(n,regs=None):c.run(s-code+sy[n],registers=regs)
 field=data+v.A4_BASE+v.A4['field_clock'];hz='ocs_clock_hz' if variant=='ocs' else 'timing_hz'
 clock='ocs_clock_state' if variant=='ocs' else 'timing_clock';a5=0x18a000
 try:
  rejects=[]
  c.intercept(s+sy['modal_bad_target'],lambda:(rejects.append(1),c.return_call()))
  for off,w,_ in specification(variant):
   old=c.read(code+off,w);c.write(code+off+w-1,bytes([old[-1]^1]));call('launch_guard',{1:code});c.write(code+off,old)
  assert len(rejects)==4
  call('launch_guard',{1:code});assert len(rejects)==4
  call('modal_install',{1:code})
  state={'rate':50,'gap':1,'ticks':0,'draws':0,'abort':False}
  def start():
   c.write(s+sy[hz],long(state['rate']));c.write(s+sy[clock],long(100)+bytes(20)+word(1)+word(0))
   c.write(s+sy['intro_active'],word(1));c.return_call()
  def world():state['ticks']+=1;c.return_call()
  def finish():
   state['draws']+=1;c.write(field,long(c.get(field,4)+state['gap']));c.return_call()
  abort=data+v.A4_BASE+(-0x707c if variant=='ocs' else -0x7094)
  def input_():
   if state['abort']:c.write(abort,word(1))
   c.return_call(0)
  for name,fn in [('intro_start',start),('intro_world',world),('intro_draw',lambda:c.return_call()),
                  ('intro_finish',finish),('intro_stop',lambda:(c.write(s+sy['intro_active'],word(0)),c.return_call())),
                  ('modal_input',input_),('modal_bar_clear',lambda:c.return_call()),('launch_hud',lambda:c.return_call()),
                  ('launch_zoom',lambda:c.return_call()),('launch_resume',lambda:c.return_call())]:c.intercept(s+sy[name],fn)
  schedules=[]
  for rate in (50,60):
   for gap in (1,3,9):
    state.update(rate=rate,gap=gap,ticks=0,draws=0,abort=False)
    c.write(field,long(100));c.write(abort,word(0));c.write(a5-8,struct.pack('>4h',40,80,120,160))
    call('launch_loop',{6:a5,11:0,13:1})
    speed=1;travel=0
    for tick in range(25):
     travel+=speed
     if tick%5==0:speed+=1
    assert state['ticks']==25 and c.reg(11)==25 and c.reg(13)==speed,(state,c.reg(11),c.reg(13),speed)
    assert struct.unpack('>4h',c.read(a5-8,8))==tuple(x-travel for x in (40,80,120,160))
    assert rate*25//10<=c.get(field,4)-100<rate*25//10+gap
    assert c.get(s+sy['intro_active'])==0
    schedules.append(dict(hz=rate,gap=gap,world_ticks=25,pictures=state['draws']))
  # Full fractional precision; integer-depth projection would repeat here.
  projections=0
  for rate in (50,60):
   c.write(s+sy[hz],long(rate))
   for depth in (9,10,11,20,40,80,160):
    for elapsed in range(rate//10):
     debt=elapsed*10;c.write(s+sy[clock]+4,long(debt))
     call('launch_scale',{9:depth,13:6})
     den=depth*rate-6*debt
     want=0 if depth<=10 or den<=10*rate else 6656*rate//den
     assert c.reg(9)==want,(rate,depth,elapsed,c.reg(9),want)
     projections+=1
  state.update(rate=50,gap=1,ticks=0,draws=0,abort=True);c.write(field,long(100));c.write(abort,word(0))
  c.write(a5-8,struct.pack('>4h',40,80,120,160));call('launch_loop',{6:a5,11:0,13:1})
  assert state['ticks']==0 and c.get(s+sy['intro_active'])==0
  # Real wait/sampling instructions; native compositor/beam advances isolated.
  pos=data+v.A4_BASE+(0x407e if variant=='ocs' else 0x488e)
  scroll=data+v.A4_BASE+(0x3f5a if variant=='ocs' else 0x476a)
  countdown=data+v.A4_BASE+(-32592 if variant=='ocs' else -32624)
  actors=data+v.A4_BASE+(-0x5a44 if variant=='ocs' else -0x5a2c)
  shown=[]
  def present():
   shown.append(struct.unpack('>5h',c.read(pos,10)))
   # Native exterior composition advances these actor records. Intermediate
   # pictures must restore them, as well as the five ship-pose words.
   c.write(actors,bytes((x+1)&255 for x in c.read(actors,120)))
   c.write(field,long(c.get(field,4)+1));c.return_call()
  c.intercept(s+sy['launch_exterior_native'],present)
  c.intercept(s+sy['launch_exterior_pose'],lambda:c.return_call())
  c.intercept(s+sy['timing_rate'],lambda:c.return_call(state['rate']))
  rooms=[]
  for rate in (50,60):
   state['rate']=rate
   for stage,steps in enumerate((10,27,23)):
    c.write(field,long(100));shown.clear()
    for tick in range(steps):
     c.write(pos,struct.pack('>5h',100,50,10,20,256));c.write(scroll,word(40));c.write(countdown,word(2))
     before=c.read(data,v.HUNKS[1][2])
     call('launch_exterior_wait',{9:stage,11:tick})
     samples=shown[-(rate//10):]
     for elapsed,sample in enumerate(samples):
      if stage<2:
       assert sample[0]==96+4*elapsed//(rate//10),('ship X',stage,elapsed,sample)
       expected_y=52-2*elapsed//(rate//10) if stage==0 else 50
       assert sample[1]==expected_y,('ship Y',stage,elapsed,sample,expected_y)
     # Only the isolated field clock can differ; presentation poses restore.
     after=bytearray(c.read(data,len(before)));f=field-data;after[f:f+4]=before[f:f+4]
     assert after==before,'exterior state leaked'
    assert c.get(field,4)-100==steps*rate//10
    if stage<2:assert len({r[0] for r in shown})>=4
    rooms.append(dict(hz=rate,stage=stage,fields=steps*rate//10,pictures=len(shown)))
  return dict(model=model,rejected_hooks=4,schedules=schedules,projections=projections,exterior=rooms,abort=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 results=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,results=results),indent=2)+'\n')
 print('PASS:',a.variant,'launch timing, projection, restoration and guards')
if __name__=='__main__':main()
