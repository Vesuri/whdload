#!/usr/bin/env python3
"""External camera sampling of native tick endpoints, restoration and cuts.

Functional CPU checks, not an emulator timing/performance measurement.
"""
import argparse, json, struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE, DATA, word, long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output, require
from variants import get
from timing_scene_check import trunc


def check(build, variant, model):
 c,sy=machine(build,variant,model);v=get(variant);ocs=variant=='ocs';a4=DATA+v.A4_BASE
 if not ocs:c.write(CODE+0x807a,struct.pack('>HI',0x4ef9,SLAVE+sy['translation_velocity']))
 def put(n,x,size=2):c.write(SLAVE+sy[n],word(x) if size==2 else long(x))
 def call(n):c.run(SLAVE-CODE+sy[n])
 def field(off,x):c.write(a4+off,word(x))
 view=-18318 if ocs else -18280
 subject=-18334 if ocs else -18296
 missile=-18316 if ocs else -18278
 target=0xcea if ocs else 0x155c
 pos=a4+v.A4['position'];vel=a4+v.A4['velocity']
 bases=(0x18d8,0x2a40,0x2d40) if ocs else (0x214a,0x3452,0x3752)
 camera=[pos+61*12]+[a4+b+61*12 for b in bases]
 def pose():return [struct.unpack('>3i',c.read(x,12)) for x in camera]
 clock='ocs_clock_state' if ocs else 'timing_clock'
 results=[]
 try:
  c.write(a4+v.A4['object_class'],bytes(128))
  field(-29954 if ocs else -29978,0)
  field(subject,1);field(missile,2);c.write(a4+target,b'\1')
  for slot in (0,1,2):
   field(v.A4['object_class']+slot*2,12 if slot!=2 else 4)
   field((0xc56 if ocs else 0x14c8)+slot*2,-1)
   field((0xcf4 if ocs else 0x1566)+slot*2,-1)
   for off,vec in zip(bases,((0,0,256),(0,256,0),(256,0,0))):
    c.write(a4+off+12*slot,struct.pack('>3i',*vec))
   c.write(pos+12*slot,struct.pack('>3i',100000+slot*10000,200000,300000+slot*20000))
   c.write(vel+12*slot,struct.pack('>3i',300,400,2000))
  for off,vec in zip(camera,((0,0,0),(0,0,256),(0,256,0),(256,0,0))):
   c.write(off,struct.pack('>3i',*vec))
  put('ocs_clock_active' if ocs else 'timing_active',1);put('intro_active',0)
  if ocs:put('ocs_prediction_cost',0,4)
  for modal,mode in ((0,4),(0,6),(0,7),(0,8),(0,14),(1,4),(1,0)):
   put('intro_active',modal)
   # Return during the moving intro leaves camera angular controls behind.
   for off in ((0xd08,0xd88,0xe08) if ocs else (0x157a,0x15fa,0x167a)):
    field(off+122,1 if modal else 0)
   field(view,mode);put('timing_scene_valid',0);put('external_seen',0)
   for hz in (50,60):
    put('ocs_clock_hz' if ocs else 'timing_hz',hz,4)
    put(clock,100,4);c.write(a4+v.A4['field_clock'],long(100))
    # Native dispatcher executes only here, at completed world endpoints.
    c.run(0x6584 if ocs else 0x680e);call('timing_scene_snapshot')
    old=pose()
    for slot in (0,1,2):
     xyz=struct.unpack('>3i',c.read(pos+12*slot,12))
     c.write(pos+12*slot,struct.pack('>3i',*(x+y for x,y in zip(xyz,(300,400,2000)))))
    c.run(0x6584 if ocs else 0x680e);call('timing_scene_snapshot');current=pose()
    require(c.get(SLAVE+sy['external_valid'])==(mode!=0),('history rejected',mode,hz))
    require(old!=current,('native camera did not move',mode,hz))
    frames=[]
    for fraction in (10,20,30,40,hz,hz+10,hz+20):
     c.write(SLAVE+sy[clock]+4,long(fraction-10));before=c.read(DATA,v.HUNKS[1][2])
     call('timing_scene_begin');got=pose()
     expected=[tuple(y+trunc((y-x)*fraction,hz) for x,y in zip(a,b)) for a,b in zip(old,current)]
     require(got==expected,('camera sample',mode,hz,fraction,got,expected))
     require(c.read(pos+12,12)!=before[pos+12-DATA:pos+24-DATA],('ship stopped',mode))
     frames.append(got);call('timing_scene_end')
     require(c.read(DATA,v.HUNKS[1][2])==before,('authoritative data changed',mode,[hex(i) for i,(x,y) in enumerate(zip(before,c.read(DATA,v.HUNKS[1][2]))) if x!=y]))
    require(len({str(x) for x in frames})==7,('camera held',mode))
    # Prove this oracle rejects a camera sampler that does nothing.
    entry=SLAVE+sy['timing_external_camera'];saved=c.read(entry,2)
    c.write(entry,word(0x4e75));call('timing_scene_begin')
    if mode!=0:require(pose()==current and pose()!=expected,('disabled sampler undetected',mode,hz))
    call('timing_scene_end');c.write(entry,saved)
    results.append(dict(modal=modal,mode=mode,hz=hz,distinct_samples=7,restored=True,disabled_sampler_rejected=(mode!=0)))
  put('intro_active',0)
  # Changing subject within the SAME view cuts history, including when the
  # renderer sees the switch before the next world snapshot.
  field(view,4);call('timing_scene_snapshot');call('timing_scene_snapshot')
  field(subject,2);before=c.read(DATA,v.HUNKS[1][2]);call('timing_scene_begin')
  require(c.get(SLAVE+sy['external_valid'])==0,'subject switch carried history')
  call('timing_scene_end');require(c.read(DATA,v.HUNKS[1][2])==before,'subject cut leaked')
  call('timing_scene_snapshot');require(c.get(SLAVE+sy['external_valid'])==0,'subject cut was forgotten')
  call('timing_scene_snapshot');require(c.get(SLAVE+sy['external_valid'])==1,'subject history never resumed')
  c.write(camera[0],long(0x40000000));call('timing_scene_snapshot')
  require(c.get(SLAVE+sy['external_valid'])==0,'teleport predicted')
  for mode in (0,3,5,9,10,11,12,13,15,-1):
   field(view,mode);call('timing_scene_snapshot')
   require(c.get(SLAVE+sy['external_valid'])==0,('nonexternal accepted',mode))
  return dict(model=model,views=results,cuts=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('cd32','ocs'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
if __name__=='__main__':main()
