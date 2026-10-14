#!/usr/bin/env python3
"""Native OCS mount placement at render cadence; no performance inference."""
import argparse,json
from pathlib import Path
from ocs_prediction_check import setup,load_scene
from ocs_clock_check import SLAVE
from ocs_display_check import CODE,DATA,word,long
from ocs_reconstruct import new_output,require


def check(build,model):
 c,sy,put,call=setup(build,model)
 try:
  load_scene(c,sy,build)
  a4=DATA+0x7ffe
  def w(off,v):c.write(a4+off,word(v))
  # Two mounts at opposite edges of the native slot range, different parents.
  c.write(a4+0xe8e,bytes(128))
  for parent in (1,9):
   w(0xe8e+2*parent,12)
   w(0x20f8+2*parent,100);w(0x2178+2*parent,80)
   w(0x252e+2*parent,200);w(0x227c+2*parent,256)
   w(0x22fc+2*parent,0);w(0x21fc+2*parent,0)
  for slot,parent,kind in ((10,1,55),(60,9,27)):
   w(0xe8e+2*slot,7);w(0xf86+2*slot,kind)
   c.write(a4+0x3058+slot,bytes([parent]))
   w(0x20f8+2*slot,12);w(0x2178+2*slot,-8)
   w(0x252e+2*slot,3);w(0x22fc+2*slot,20)
   w(0x29ba+2*slot,160)
  raw=c.read(DATA,0xf5b8)
  call('ocs_exhaust_capture')
  c.run(0x2837a)
  authoritative=c.read(DATA,0xf5b8)
  samples=[];cases=0
  for hz in (50,60):
   for mirror in (0,16,32,48):
    for phase in range(hz//10+1):
     c.write(DATA,authoritative)
     call('timing_scene_save_active');put('timing_scene_staged',1)
     # Geometry output of a moving/rolling parent at successive render fields.
     for parent in (1,9):
      w(0x20f8+parent*2,100+phase*3);w(0x2178+parent*2,80-phase*2)
      w(0x252e+parent*2,200+phase);w(0x227c+parent*2,256+phase*8)
      w(0x22fc+parent*2,phase*7);w(0x21fc+parent*2,mirror)
     projected=c.read(DATA,0xf5b8)
     # Independent oracle: fresh mount inputs, native angle and native placement.
     for slot,parent in ((10,1),(60,9)):
      for off in (0x20f8,0x2178,0x252e):
       start=0x7ffe+off+2*slot;c.write(DATA+start,raw[start:start+2])
      c.run(0x2816a,word(parent)+word(20));w(0x22fc+2*slot,c.reg(9))
     c.run(0x2837a);expected=c.read(DATA,0xf5b8)
     c.write(DATA,projected);call('ocs_exhaust_draw')
     require(c.read(DATA,0xf5b8)==expected,('native mount mismatch',model,hz,mirror,phase))
     samples.append([c.get(a4+off+20) for off in (0x20f8,0x2178,0x252e,0x22fc,0x227c)])
     call('ocs_exhaust_draw')
     require(c.read(DATA,0xf5b8)==expected,'offsets accumulated across redraws')
     call('timing_scene_end')
     require(c.read(DATA,0xf5b8)==authoritative,'authoritative/RNG/lifecycle leak')
     cases+=1
  require(len({tuple(x) for x in samples[:6]})==6,'mount stayed at tick position')
  # Capture must invert both mirror flags, including wrapped mount angles.
  for mirror in (0,16,32,48):
   c.write(DATA,raw)
   for parent in (1,9):
    w(0x21fc+2*parent,mirror);w(0x22fc+2*parent,350)
   for slot,parent in ((10,1),(60,9)):
    c.run(0x2816a,word(parent)+word(20));w(0x22fc+2*slot,c.reg(9))
   call('ocs_exhaust_capture');c.run(0x2837a)
   expected=c.read(DATA,0xf5b8);call('ocs_exhaust_draw')
   require(c.read(DATA,0xf5b8)==expected,'mirrored capture changed native pose')
  # Rebase invalidates stale mount data. Dead/reused identities are not restored.
  c.write(DATA,authoritative);call('ocs_prediction_rebase')
  before=c.read(DATA,0xf5b8);call('ocs_exhaust_draw')
  require(c.read(DATA,0xf5b8)==before,'rebase used old mounts')
  put('ocs_exhaust_valid',1)
  for kind in (0,4):
   c.write(DATA,authoritative);w(0xe8e+20,kind)
   before=c.read(DATA,0xf5b8);call('ocs_exhaust_draw')
   for off in (0x20f8,0x2178,0x252e,0x22fc):
    start=0x7ffe+off+20
    require(c.read(DATA+start,2)==before[start:start+2],'reused slot modified')
  c.write(DATA,authoritative);w(0x20f8+2,0x8001);call('ocs_exhaust_draw')
  require(c.get(a4+0x20f8+20)==0x8001,'invisible parent left visible flame')
  return dict(model=model,cases=cases,samples=samples[:6],whole_data_restored=True,repeat_draw_exact=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,m) for m in (1,2,4)]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS:',sum(x['cases'] for x in rows),'native mount cases')
if __name__=='__main__':main()
