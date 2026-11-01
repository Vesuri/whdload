#!/usr/bin/env python3
"""Execute native flight/marker code and assert layering at its drawing boundary.
Graphics sinks are synthetic; this is an ordering/ABI test, not a pixel emulator.
"""
import argparse,json,struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE,DATA,STACK,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output,require


def check(build,variant,model):
 c,sy=machine(build,variant,model);ocs=variant=='ocs';a4=DATA+0x7ffe
 early,late,draw=(0x30e,0x322,0x2e6) if ocs else (0x30c,0x320,0x2e4)
 marker,scene=(0x34e0,0x28548) if ocs else (0x3766,0x294d4)
 active=SLAVE+sy['ocs_clock_active' if ocs else 'timing_active']
 events=[];bitmap=[];state={'sensor':5,'z':25600}
 # OCS test setup installs candidate hooks; explicitly restore native calls
 # for the original-order control rather than accidentally testing a wrapper.
 saved={early:word(0x4eb9)+long(CODE+marker),late:word(0x4eb9)+long(CODE+scene)}
 def noop():c.return_call()
 def scene_sink():
  require(c.get(c.reg(8)+4)==state['scene_arg'],'scene argument changed')
  events.append('world');c.return_call(0x12345678)
 def raster():events.append('world');c.return_call(0x12345678)
 def sink():
  args=struct.unpack('>IhhIH',c.read(c.reg(8)+4,14))
  require(args[1:3]==(160,64) and args[-1]==3,('native marker coordinates/frame',args))
  bitmap.append(args);events.append('marker');c.return_call()
 def transform():
  c.write(c.get(c.reg(8)+8,4),struct.pack('>iii',0,0,state['z']));c.return_call()
 try:
  for off in ((0x15d1c,0x322e0,0x9618,0x363e,0x2ba2c) if ocs else (0x15fb4,0x31cd6,0x98a2,0x38c4)):
   c.intercept(CODE+off,noop)
  c.intercept(CODE+scene,scene_sink)
  if ocs:c.intercept(CODE+0x2bab4,raster)
  c.intercept(CODE+(0x1e0a if ocs else 0x2092),lambda:c.return_call(state['sensor']))
  c.intercept(CODE+(0x2b930 if ocs else 0x2c8bc),lambda:c.return_call(25600))
  c.intercept(CODE+(0x2abfa if ocs else 0x2bb86),transform)
  c.intercept(CODE+(0x2f9a6 if ocs else 0x2efe8),sink)
  # Forward camera fixture; actual native marker eligibility and projection
  # remain executing. The camera transform and bitmap are boundary stubs.
  for off,value in ((-4184 if ocs else -4314,160),(-4182 if ocs else -4312,64),
                    (-4188 if ocs else -4318,320),(0x1304 if ocs else 0x1b76,1),
                    (-18320 if ocs else -18282,0),(-32600 if ocs else -32630,0)):
   c.write(a4+off,word(value))
  rows=[]
  for patched,enabled in ((False,False),(True,False),(True,True)):
   for off in (early,late):c.write(CODE+off,saved[off])
   if patched:
    for off,name in ((early,'waypoint_early'),(late,'waypoint_scene')):
     c.write(CODE+off,word(0x4eb9)+long(SLAVE+sy[name]))
   for view in (0,1,2,3,4,15):
    for sensor,z in ((5,25600),(0,25600),(5,-25600)):
     for scene_arg in (0,1):
      state.update(sensor=sensor,z=z,scene_arg=scene_arg);events.clear();bitmap.clear()
      c.write(active,word(enabled));c.write(a4+(-18318 if ocs else -18280),word(view))
      c.write(a4+(0x904 if ocs else 0x1176),long(scene_arg))
      c.write(a4+(-32592 if ocs else -32624),word(1))
      c.write(a4+(-32590 if ocs else -32622),word(1))
      before=c.read(DATA,0xf5b8 if ocs else 0xfda0)
      c.run(draw)
      visible=view in (0,4) and sensor==5 and z>0
      # The reorder is independent of the flight clock: every patched mode.
      want=(['world','marker'] if patched else ['marker','world']) if visible else ['world']
      require(events==want,(patched,enabled,view,sensor,z,events,want))
      require(c.reg(8)==STACK+4 and c.reg(9)==1,'flight return ABI')
      # Only native draw_count changes in this isolated native composition.
      after=bytearray(c.read(DATA,len(before)));count=0x7ffe+(2272 if ocs else 4434)
      after[count:count+2]=before[count:count+2]
      require(bytes(after)==before,'marker moved gameplay data')
      rows.append((patched,enabled,view,sensor,z,scene_arg))
  return dict(model=model,cases=len(rows),original_marker_before_world=True,
              patched_marker_after_world_any_clock=True,native_visibility_retained=True,
              scene_argument_retained=True,gameplay_data_unchanged=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'))
 p.add_argument('build',type=Path);p.add_argument('--output',required=True);a=p.parse_args()
 out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,results=rows),indent=2)+'\n')
 print(rows)
if __name__=='__main__':main()
