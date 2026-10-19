#!/usr/bin/env python3
"""Afterburn/braking transitions must retain intermediate world and camera poses."""
import argparse, json, struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE, DATA, word, long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output, require
from variants import get
from timing_scene_check import trunc


def check(build, variant, model):
 c, sy = machine(build, variant, model)
 v = get(variant); ocs = variant == 'ocs'; a4 = DATA + v.A4_BASE
 def put(n, x, size=2): c.write(SLAVE+sy[n], word(x) if size == 2 else long(x))
 def call(n): c.run(SLAVE-CODE+sy[n])
 def field(off, x): c.write(a4+off, word(x))
 action = 0xcf4 if ocs else 0x1566
 pos = a4+v.A4['position']; vel = a4+v.A4['velocity']
 clock = 'ocs_clock_state' if ocs else 'timing_clock'
 samples = controls = 0
 try:
  c.write(a4+v.A4['object_class'], bytes(128))
  field(-18318 if ocs else -18280, 0); field(-29954 if ocs else -29978, 0)
  for slot in (0,1,2):
   field(v.A4['object_class']+2*slot, 12 if slot == 0 else 4)
   field((0xc56 if ocs else 0x14c8)+2*slot, -1)
   for off, vec in zip(((0x18d8,0x2a40,0x2d40) if ocs else (0x214a,0x3452,0x3752)), ((0,0,256),(0,256,0),(256,0,0))):
    c.write(a4+off+12*slot, struct.pack('>3i', *vec))
   c.write(pos+12*slot, struct.pack('>3i',10000,20000,30000))
   c.write(vel+12*slot, struct.pack('>3i',5000,-500,100))
  put('ocs_clock_active' if ocs else 'timing_active',1)
  put('translation_active',1)
  if ocs: put('ocs_prediction_cost',0,4)
  for hz in (50,60):
   put('ocs_clock_hz' if ocs else 'timing_hz',hz,4)
   put(clock,100,4); c.write(a4+v.A4['field_clock'],long(100))
   for old in (-1,1,3):
    for new in (-1,1,3):
     field(action,old);field(action+2,old)
     call('timing_scene_snapshot');call('timing_scene_snapshot')
     # Slot 1 also exercises actual ship-class snapshot eligibility.
     field(v.A4['object_class']+2,12)
     call('timing_scene_snapshot');call('timing_scene_snapshot')
     field(action,new);field(action+2,new)
     call('timing_scene_snapshot')
     require(c.read(SLAVE+sy['timing_scene_predictable'],3)==b'\1\1\1',('transition cut',old,new))
     field(v.A4['object_class']+2,4)
     call('timing_scene_snapshot');call('timing_scene_snapshot')
     call('timing_player_camera')
     for fraction in (10,20,30,40):
      c.write(SLAVE+sy[clock]+4,long(fraction-10))
      before=c.read(DATA,v.HUNKS[1][2])
      call('timing_scene_begin')
      for slot in (1,2):
       got=struct.unpack('>3i',c.read(pos+12*slot,12))
       want=tuple(p+trunc(x*fraction,hz) for p,x in zip((10000,20000,30000),(5000,-500,100)))
       require(got==want,('world stopped',old,new,hz,fraction,slot,got,want))
      require(c.read(pos,12)!=before[pos-DATA:pos-DATA+12],'player display lead skipped')
      require(c.read(pos+61*12,12)!=before[pos-DATA+61*12:pos-DATA+62*12],'camera display lead skipped')
      call('timing_scene_end')
      require(c.read(DATA,v.HUNKS[1][2])==before,'render changed authoritative data')
      samples+=1
   for old,new in ((-1,4),(4,1),(1,5),(5,-1)):
    field(action,-1);field(action+2,old)
    call('timing_scene_snapshot');call('timing_scene_snapshot')
    field(action+2,new);call('timing_scene_snapshot')
    require(c.get(SLAVE+sy['timing_scene_predictable']+1,1)==0,'script transition accepted')
    controls+=1
   for off,value in ((action,4),(-18318 if ocs else -18280,9),(-29954 if ocs else -29978,1)):
    field(action,-1);field(-18318 if ocs else -18280,0);field(-29954 if ocs else -29978,0)
    call('timing_scene_snapshot');call('timing_scene_snapshot')
    field(off,value);before=c.read(DATA,v.HUNKS[1][2]);call('timing_scene_begin');call('timing_scene_end')
    require(c.read(DATA,v.HUNKS[1][2])==before,'cut changed data')
    require(c.get(SLAVE+sy['timing_scene_valid'])==0,'unsafe view accepted')
    controls+=1
   field(-29954 if ocs else -29978,0)
  return dict(model=model,samples=samples,rejected_controls=controls)
 finally: c.close()


def steering(build, variant, model):
 c,sy=machine(build,variant,model);v=get(variant);ocs=variant=='ocs';a4=DATA+v.A4_BASE
 def put(n,x,size=2):c.write(SLAVE+sy[n],word(x) if size==2 else long(x))
 def call(n,args=b'',registers=None):c.run(SLAVE-CODE+sy[n],args,registers)
 def field(off,x):c.write(a4+off,word(x))
 action=0xcf4 if ocs else 0x1566
 ramp=0xe88 if ocs else 0x16fa
 angles=(0xd88,0xd08,0xe08) if ocs else (0x15fa,0x157a,0x167a)
 bases=(0x18d8,0x2a40,0x2d40) if ocs else (0x214a,0x3452,0x3752)
 controller,mapper,rotation=(0x183e4,0x73e,0x79fc) if ocs else (0x18daa,0x742,0x7c86)
 hooks=(0x18528,0x1853a,0x18574) if ocs else (0x18eee,0x18f00,0x18f3a)
 for off,label in zip(hooks,('timing_throttle_gate','timing_throttle_gate','timing_fire_gate')):
  c.write(CODE+off,word(0x4eb9)+long(SLAVE+sy[label]))
 native=[]
 c.intercept(CODE+rotation,lambda:native.append(1))
 cases=0
 try:
  field(v.A4['object_class'],12)
  field(-18318 if ocs else -18280,0);field(-29954 if ocs else -29978,0)
  # Native held-axis input images differ between the two executables.
  c.write(DATA+(0xbe52 if ocs else 0xc642),bytes(128))
  pad=a4+0x3ed4 if ocs else DATA+0xc6c2
  for hz in (50,60):
   put('ocs_clock_hz' if ocs else 'timing_hz',hz,4)
   for axis in range(4):
    c.write(pad,bytes(int(i==axis) for i in range(6)))
    for thrust in (-1,1,3,-1):
     field(action,thrust)
     for off in (ramp,ramp+2,ramp+4):field(off,7)
     before=c.read(DATA,v.HUNKS[1][2])
     call('timing_preview_controls')
     require(c.read(DATA,v.HUNKS[1][2])==before,'steering preview leaked native state')
     got=c.read(SLAVE+sy['timing_angles'],6)
     put('timing_preview',1);c.run(controller);c.run(mapper);put('timing_preview',0)
     want=b''.join(c.read(a4+off,2) for off in angles)
     require(got==want and got!=bytes(6),('afterburn steering disabled',thrust,axis,hz,got.hex(),want.hex()))
     c.write(DATA,before)
     for off,vec in zip(bases,((0,0,256),(0,256,0),(256,0,0))):
      c.write(a4+off,struct.pack('>3i',*vec))
     c.write(SLAVE+sy['timing_angle_remainder'],bytes(12))
     # Camera changes within the interval; small integer angles may need
     # more than one field to accumulate a whole native angular unit.
     call('timing_player_camera')
     changes=0
     for _ in range(hz//10):
      previous=b''.join(c.read(a4+off+61*12,12) for off in bases)
      call('timing_player_field');call('timing_player_camera')
      changes+=previous!=b''.join(c.read(a4+off+61*12,12) for off in bases)
     require(changes>=2,('camera held until world tick',thrust,axis,hz,changes))
     put('timing_in_world',1);native.clear()
     basis=b''.join(c.read(a4+off,12) for off in bases)
     call('timing_world_rotation',word(0),{11:0})
     require(not native,'world duplicated field rotation')
     require(basis==b''.join(c.read(a4+off,12) for off in bases),'world changed field-owned basis')
     cases+=1
  # Scripted thrust retains native rotation; never broaden ownership to it.
  field(action,4);native.clear();call('timing_world_rotation',word(0),{11:0})
  require(len(native)==1,'script rotation lost native owner')
  call('timing_preview_controls');require(c.read(SLAVE+sy['timing_angles'],6)==bytes(6),'script preview accepted')
  return dict(model=model,steering_cases=cases,preview_isolated=True,field_camera=True,no_double_rotation=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('cd32','ocs'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[dict(presentation=check(a.build,a.variant,m),steering=steering(a.build,a.variant,m)) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
if __name__=='__main__': main()
