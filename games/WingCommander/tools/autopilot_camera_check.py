#!/usr/bin/env python3
"""Compare fly-by camera drift/aim with the native camera-12 geometry."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import ROOT,new_output,require
from variants import get
from timing_scene_check import trunc


def check(build,variant,model):
 ocs=variant=='ocs'
 if ocs:c,sy,_,_=setup(build,model)
 else:
  c=Native(ROOT/get(variant).GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(SLAVE,(build/'payload.bin').read_bytes());c.write(SLAVE+sy['timing_game'],long(CODE))
 a4=DATA+0x7ffe
 pos,vel,kind,view,bases,angles=(0x92a,0x14fc,0xe8e,-18318,(0x18d8,0x2a40,0x2d40),(0xd88,0xd08,0xe08)) if ocs else (0x119c,0x1d6e,0x1700,-18280,(0x214a,0x3452,0x3752),(0x15fa,0x157a,0x167a))
 size=0xf5b8 if ocs else 0xfda0;clock='ocs_clock_state' if ocs else 'timing_clock'
 def put(n,v,sz=2):c.write(SLAVE+sy[n],word(v) if sz==2 else long(v))
 def run(n):c.run(SLAVE-CODE+sy[n])
 def vec(off,slot):return struct.unpack('>3i',c.read(a4+off+slot*12,12))
 def setvec(off,slot,v):c.write(a4+off+slot*12,struct.pack('>3i',*v))
 cases=0
 try:
  c.write(a4+kind,bytes(128));c.write(a4+kind,word(4));c.write(a4+view,word(12))
  c.write(a4+(-29954 if ocs else -29978),word(0))
  put('intro_active',1);put('ocs_clock_active' if ocs else 'timing_active',0)
  put('ocs_pending' if ocs else 'release_pending',0)
  if ocs:put('ocs_prediction_cost',0,4)
  for off in angles:c.write(a4+off,bytes(128))
  for right in ((256,0,0),(192,0,160)):
   for off,v in zip(bases,((0,0,256),(0,256,0),right)):
    setvec(off,61,v);setvec(off,0,v)
   setvec(pos,0,(20000,3000,50000));setvec(vel,0,(7000,0,-2000))
   setvec(pos,61,(-10000,9000,12000));setvec(vel,61,(2000,500,1000))
   original=c.read(DATA,size);start=vec(pos,61)
   # Execute the entire original camera dispatcher once for its true drift.
   c.run(0x6584 if ocs else 0x680e)
   endpoint=vec(pos,61);delta=tuple(b-a for a,b in zip(start,endpoint))
   require(delta==tuple(v-10*r for v,r in zip((2000,500,1000),right)),('native drift',delta))
   c.write(DATA,original)
   put('timing_scene_valid',0);run('timing_scene_snapshot');run('timing_scene_snapshot')
   for hz in (50,60):
    put('ocs_clock_hz' if ocs else 'timing_hz',hz,4);put(clock,100,4)
    c.write(a4+(-2048 if ocs else -252),long(100))
    for fraction in range(10,hz+21,10):
     c.write(SLAVE+sy[clock]+4,long(fraction-10));before=c.read(DATA,size)
     run('timing_scene_begin');shown=c.read(DATA,size)
     expected=tuple(a+trunc(v*fraction,hz)+trunc(-10*r*fraction,hz) for a,v,r in zip(start,(2000,500,1000),right))
     require(vec(pos,61)==expected,('missing drift',vec(pos,61),expected,delta))
     got=tuple(vec(off,61) for off in bases)
     # Aim must match native geometry using the staged player/camera pair.
     for off in bases:
      c.write(a4+off+732,before[0x7ffe+off+732:0x7ffe+off+744])
     c.run(0x29894 if ocs else 0x2a820,word(0))
     require(tuple(vec(off,61) for off in bases)==got,'aim did not follow staged player')
     c.write(DATA,shown);run('timing_scene_end')
     require(c.read(DATA,size)==before,'fly-by render state leaked')
     cases+=1
   c.write(DATA,original)
  return dict(model=model,cases=cases,native_drift_and_aim=True,exact_restoration=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
if __name__=='__main__':main()
