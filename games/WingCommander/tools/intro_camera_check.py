#!/usr/bin/env python3
"""Native intro camera basis samples and exact authoritative restoration.

The oracle runs native whole-angle rotations, then independently samples their
basis endpoints. It checks presentation arithmetic, not native trig accuracy or
performance. One-unit controls catch the old whole-angle rounding defect.
"""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import CODE,DATA,word,long
from ocs_reconstruct import ROOT,new_output,require
from timing_audit_check import CPU
from cd32_runtime import locate
from timing_scene_check import trunc


def check(build,variant,model):
 if variant=='ocs':
  c,sy,_,_=setup(build,model);code,data,s=CODE,DATA,SLAVE
  basis=(0x98d6,0xaa3e,0xad3e);angles=(0x8d86,0x8d06,0x8e06)
  calls=(0x29d26,0x29d66,0x29da6);view=0x3870;field=0x77fe;size=0xf5b8
  active,clock,hzname,pending='ocs_clock_active','ocs_clock_state','ocs_clock_hz','ocs_pending'
 else:
  memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes()
  c=CPU(memory,locate(memory),model);code,data,s=c.code,c.data,0x180000
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],long(code))
  basis=(0xa148,0xb450,0xb750);angles=(0x95f8,0x9578,0x9678)
  calls=(0x2acb2,0x2acf2,0x2ad32);view=0x3896;field=0x7f02;size=0xfda0
  active,clock,hzname,pending='timing_active','timing_clock','timing_hz','release_pending'
 def put(n,v,sz=2):c.write(s+sy[n],word(v) if sz==2 else long(v))
 def run(n):c.run(s-code+sy[n])
 def vectors():return tuple(struct.unpack('>3i',c.read(data+o+732,12)) for o in basis)
 def set_vectors(v):
  for o,vec in zip(basis,v):c.write(data+o+732,struct.pack('>3i',*vec))
 cases=0;controls=0;examples=[]
 try:
  put(active,0);put('intro_active',1);put(pending,0)
  if variant=='ocs':put('ocs_prediction_cost',0,4)
  c.write(data+(0x8e8c if variant=='ocs' else 0x96fe),bytes(128))
  c.write(data+view,word(15))
  initial=((0,0,256),(0,256,0),(256,0,0))
  for orientation in (0,27):
   set_vectors(initial)
   if orientation:c.run(calls[2],struct.pack('>hh',orientation,61))
   start=vectors()
   for rates in ((-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1),(2,-3,1),(0,0,0)):
    set_vectors(start)
    for rate,entry in zip(rates,calls):
     if rate:c.run(entry,struct.pack('>hh',rate,61))
    end=vectors();set_vectors(start)
    for off,rate in zip(angles,rates):c.write(data+off+122,word(rate))
    put('timing_scene_valid',0);run('timing_scene_snapshot');run('timing_scene_snapshot')
    for hz in (50,60):
     put(hzname,hz,4);put(clock,100,4);c.write(data+field,long(100))
     samples=[]
     for fraction in range(0,hz+21,10):
      # Predictor includes one publication field; debt chooses the remainder.
      c.write(s+sy[clock]+4,long(max(0,fraction-10)))
      effective=max(10,fraction)
      before=c.read(data,size);run('timing_scene_begin')
      got=vectors();want=tuple(tuple(a+trunc((b-a)*effective,hz) for a,b in zip(x,y)) for x,y in zip(start,end))
      require(got==want,('basis sample',variant,model,rates,hz,effective,got,want))
      run('timing_scene_end');require(c.read(data,size)==before,('camera state leaked',[(hex(i),a,b) for i,(a,b) in enumerate(zip(before,c.read(data,size))) if a!=b][:20]))
      samples.append(got);cases+=1
     if rates in ((-1,0,0),(0,-1,0),(0,0,-1)):
      require(len(set(samples[:hz//10]))>=3,'one-unit camera turn still steps')
      # Old angle truncation is unchanged below one tick; fail that control.
      require(samples[hz//10-2]!=start,'old whole-angle control survived')
      controls+=1
      if orientation==0:examples.append(dict(hz=hz,rates=rates,bases=samples[:hz//10]))
  # An actual view cut must suppress staging, even with a moving camera.
  c.write(data+angles[0]+122,word(-1))
  run('timing_scene_snapshot');run('timing_scene_snapshot')
  c.write(data+view,word(8));before=c.read(data,size);run('timing_scene_begin')
  require(vectors()==start,'camera view cut predicted');run('timing_scene_end')
  require(c.read(data,size)==before,'view cut leaked')
  require(c.read(s+sy['timing_scene_valid'],2)==bytes(2),'view cut not invalidated')
  put('intro_active',0);c.write(data+view,word(15))
  run('timing_scene_snapshot');run('timing_scene_snapshot')
  before=c.read(data,size);run('timing_scene_begin');run('timing_scene_end')
  require(c.read(data,size)==before,'disabled intro changed camera')
  return dict(model=model,cases=cases,rejected_whole_angle_controls=controls,examples=examples)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 results=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,models=results),indent=2)+'\n')
 print(a.variant,[(r['model'],r['cases'],r['rejected_whole_angle_controls']) for r in results])
if __name__=='__main__':main()
