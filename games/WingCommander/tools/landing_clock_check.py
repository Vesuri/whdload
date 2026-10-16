#!/usr/bin/env python3
"""Native landing script differential, redraw isolation and clock checks."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import Native,CODE,DATA,STACK,word,long
from ocs_reconstruct import ROOT,new_output
from variants import get
from landing_source import specification


def check(build,variant,model):
 v=get(variant);s=SLAVE;ocs=variant=='ocs'
 if ocs:c,sy,_,_=setup(build,model)
 else:
  c=Native(ROOT/v.GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],long(CODE))
 base=DATA+v.A4_BASE;field=base+v.A4['field_clock'];scroll=base+(0x3f5a if ocs else 0x476a)
 actors=base+(-0x5a44 if ocs else -0x5a2c);frame=base+0x6000
 state={};rows=[]
 def call(n,regs=None):c.run(s-CODE+sy[n],registers=regs)
 def input_sample():
  c.write(field,long(c.get(field,4)+state['gap']))
  c.return_call(1 if state.get('abort_at') and c.reg(11)>=state['abort_at'] else 0)
 def actor():
  slot=c.get(c.reg(8)+4);p=actors+slot*24
  c.write(p,word(c.get(p)+c.get(p+4)));c.write(p+2,word(c.get(p+2)+c.get(p+6)))
  if c.get(p+10,1):c.write(p+9,bytes([(c.get(p+9,1)+1)&255]))
  c.return_call()
 def sound():state['sound']+=1;c.return_call(0)
 def draw_sample():state['samples'].append((c.reg(11),c.reg(13)&65535,c.reg(14)&65535))
 try:
  # Native calls outside the script under test: graphics/OS and sound fixtures.
  pairs=[(0xba8,0xc68),(0x2f9a6,0x2efe8),(0x2d0de,0x2d746),(0x3260a,0x31fc2),
         (0x2a816,0x2b7a2),(0x31e98,0x3188e),(0x31edc,0x318d2),(0x2f3a0,0x2ec98)]
  for a,b in pairs:c.intercept(CODE+(a if ocs else b),lambda:c.return_call())
  for a,b in [(0x1464c,0x148d6),(0x146b0,0x1493a),(0x1464a,0x148d4)]:c.intercept(CODE+(a if ocs else b),sound)
  c.intercept(CODE+(0x1d3a0 if ocs else 0x1e0ce),actor)
  c.intercept(CODE+(0x180c4 if ocs else 0x1898a),input_sample)
  c.intercept(s+sy['modal_input'],input_sample)
  c.intercept(s+sy['landing_rate'],lambda:c.return_call(state['rate']))
  ends=(0x1a792,0x1ab50) if ocs else (0x1b4da,0x1b898)
  for end in ends:c.intercept(CODE+end,lambda:c.return_call())
  original=c.read(DATA,65536)
  def reset(stage,rate=50,gap=1,abort_at=0):
   c.write(DATA,original);state.clear();state.update(rate=rate,gap=gap,abort_at=abort_at,sound=0,samples=[])
   c.write(field,long(0xfffffff0));c.write(scroll,word(520 if stage==0 else 0)+word(64 if stage==0 else 0))
   c.write(frame-78,word(60)+word(10));c.write(base+(0x29ba if ocs else 0x33cc),word(256))
   for i in range(5):c.write(actors+i*24,word(100+i)+word(110+i)+word(-4)+word(1)+bytes([0,0,1,0])+bytes(12))
   return {6:frame,11:0,12:1 if stage==0 else 250,13:64 if stage==0 else 16,14:20 if stage==0 else 180,15:20 if stage==0 else 100,16:16 if stage==0 else 1,3:0,4:0}
  def result():return dict(regs=[c.reg(r) for r in range(11,17)],scroll=c.read(scroll,4).hex(),actors=c.read(actors,120).hex(),locals=c.read(frame-78,4).hex(),sound=state['sound'])
  native=[]
  for stage in range(2):
   regs=reset(stage);c.run(specification(variant)[stage][0],registers=regs);native.append(result())
  rejects=[];c.intercept(s+sy['modal_bad_target'],lambda:(rejects.append(1),c.return_call()))
  for off,width,_ in specification(variant):
   old=c.read(CODE+off,width)
   for i in range(width):
    bad=bytearray(old);bad[i]^=1;c.write(CODE+off,bytes(bad));call('landing_guard',{1:CODE})
   c.write(CODE+off,old)
  call('landing_guard',{1:CODE});assert len(rejects)==50,len(rejects)
  call('landing_install',{1:CODE})
  for name in ('landing_draw0','landing_draw1'):c.intercept(s+sy[name],draw_sample)
  for rate in (50,60):
   for gap in (1,9):
    for stage in range(2):
     regs=reset(stage,rate,gap);c.run(specification(variant)[stage][0],registers=regs)
     assert result()==native[stage],(stage,result(),native[stage])
     assert c.reg(8)==STACK+4
     elapsed=(c.get(field,4)-0xfffffff0)&0xffffffff
     ticks=100 if stage==0 else 85
     assert ticks*rate//10<=elapsed<=max(ticks*rate//10,ticks*gap)+2*gap,(stage,rate,gap,elapsed)
     if gap==1:assert any(x[0]==y[0] and x[1:]!=y[1:] for x,y in zip(state['samples'],state['samples'][1:])),state['samples'][:30]
     rows.append(dict(stage=stage,rate=rate,gap=gap,fields=elapsed,pictures=len(state['samples'])))
  for stage in range(2):
   c.run(specification(variant)[stage][0],registers=reset(stage,abort_at=3));assert c.reg(11)==3
  # Perspective division retains fractional depth; no integer-depth plateaus.
  for stage,old,new,base_scale in ((0,20,22,4096),(1,100,99,24576)):
   for fields in (5,6):
    c.write(s+sy['landing_stage'],word(stage));c.write(s+sy['landing_fields'],word(fields))
    c.write(s+sy['landing_previous']+6,word(old));c.write(s+sy['landing_next']+6,word(new))
    samples=[]
    for f in range(fields):
     c.write(s+sy['landing_elapsed'],word(f));call('landing_scale',{9:base_scale,11:3})
     assert c.reg(9)==base_scale*fields//(old*fields+(new-old)*f)
     samples.append(c.reg(9))
    assert len(set(samples))>1
  return dict(model=model,native=native,schedules=rows,guards=50,abort_stages=2)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 r=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,results=r),indent=2)+'\n');print('PASS',a.variant,'landing clock, native script, redraw isolation and zoom')
if __name__=='__main__':main()
