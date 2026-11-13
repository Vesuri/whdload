#!/usr/bin/env python3
"""Field maintenance ownership and bounded asteroid/mine pose regression."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import ROOT,new_output,require
from variants import get
from timing_scene_check import trunc


def machine(build,variant,model,german=False):
 """German (CD32 release builds): wing.german with the slave's German words."""
 if variant=='ocs':
  c,sy,_,_=setup(build,model)
 else:
  if german:
   import german_map
   c=Native(ROOT/german_map.GERMAN[0],model=model,variant=variant,game_sha=german_map.GERMAN[1])
  else:c=Native(ROOT/get(variant).GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(SLAVE,(build/('german.bin' if german else 'payload.bin')).read_bytes());c.write(SLAVE+sy['timing_game'],long(CODE))
 return c,sy


def owners(build,variant,model):
 c,sy=machine(build,variant,model);v=get(variant);a4=DATA+v.A4_BASE;ocs=variant=='ocs'
 def put(n,x):c.write(SLAVE+sy[n],word(x))
 def call(n):c.run(SLAVE-CODE+sy[n])
 try:
  events=[]
  def noop():c.return_call()
  for off in ((0x2be,0x290fa,0x27cfa,0x281c0,0x2837a,0x2018,0x3908,0xacfa) if ocs else (0x2a8,0x2a086,0x15fb4)):
   c.intercept(CODE+off,noop)
  for n in (('ocs_clock_score','ocs_clock_sim_native','ocs_exhaust_capture') if ocs else ('timing_player_camera','timing_debris_original')):
   c.intercept(SLAVE+sy[n],noop)
  def maintenance():
   require(c.get(a4+v.A4['draw_count'])==7,'cleanup still uses render count')
   events.append('field');c.write(a4+v.A4['object_class']+68,word(4));c.return_call()
  def snapshot():events.append('snapshot');c.return_call()
  c.intercept(CODE+v.NATIVE['asteroids'],maintenance)
  c.intercept(SLAVE+sy['ocs_prediction_snapshot' if ocs else 'timing_scene_snapshot'],snapshot)
  active='ocs_clock_active' if ocs else 'timing_active'
  draw='ocs_clock_asteroids_draw' if ocs else 'intro_asteroids_draw'
  put(active,1);put('intro_active',0)
  c.write(a4+v.A4['world_count'],word(7));c.write(a4+v.A4['draw_count'],word(99))
  c.write(a4+(0x904 if ocs else 0x1176),long(0x180000))
  call('ocs_clock_tick' if ocs else 'timing_scene_tick')
  require(events==['field','snapshot'],('field must precede snapshot',events))
  require(c.get(a4+v.A4['draw_count'])==99,'draw counter leaked')
  events.clear()
  for _ in range(8):call(draw)
  require(not events,'flight drawing mutated field')
  put(active,0);put('intro_active',1);call(draw)
  require(not events,'intro drawing mutated field')
  if not ocs:
   call('intro_world');require(events==['field','snapshot'],'intro missing/duplicate field work')
   events.clear()
  put('intro_active',0);c.write(a4+v.A4['draw_count'],word(7));call(draw)
  require(events==['field'],'original path suppressed')
  return dict(world_before_snapshot=True,cleanup_world_counter=True,draw_suppressed=True,native_fallback=True)
 finally:c.close()


def poses(build,variant,model):
 c,sy=machine(build,variant,model);v=get(variant);a4=DATA+v.A4_BASE;ocs=variant=='ocs'
 def put(n,x,size=2):c.write(SLAVE+sy[n],word(x) if size==2 else long(x))
 def call(n):c.run(SLAVE-CODE+sy[n])
 try:
  # The field constructor uses models 33 (mine), 34..38 (asteroids).
  # Exercise each identity with the shared constant-velocity predictor and
  # prove that intermediate poses cannot leak into authoritative game data.
  c.write(a4+v.A4['object_class'],bytes(128))
  c.write(a4+(-18318 if ocs else -18280),word(0));c.write(a4+(-29954 if ocs else -29978),word(0))
  c.write(a4+v.A4['object_class'],word(12));c.write(a4+(0xcf4 if ocs else 0x1566),word(-1))
  for slot in (0,*range(34,40)):
   c.write(a4+v.A4['object_class']+slot*2,word(12 if slot==0 else (10 if slot==34 else 9)))
   c.write(a4+(0xf86 if ocs else 0x17f8)+slot*2,word(0 if slot==0 else slot-1))
   c.write(a4+(0xc56 if ocs else 0x14c8)+slot*2,word(-1))
   for off,vec in zip(((0x18d8,0x2a40,0x2d40) if ocs else (0x214a,0x3452,0x3752)),((0,0,256),(0,256,0),(256,0,0))):
    c.write(a4+off+slot*12,struct.pack('>3i',*vec))
   c.write(a4+v.A4['position']+slot*12,struct.pack('>3i',10000,20000,30000))
   c.write(a4+v.A4['velocity']+slot*12,struct.pack('>3i',5121,-513,1))
  put('ocs_clock_active' if ocs else 'timing_active',1);put('intro_active',0)
  if ocs:put('ocs_prediction_cost',0,4)
  call('timing_scene_snapshot');call('timing_scene_snapshot')
  samples=0
  for hz in (50,60):
   put('ocs_clock_hz' if ocs else 'timing_hz',hz,4)
   clock='ocs_clock_state' if ocs else 'timing_clock';put(clock,100,4)
   c.write(a4+v.A4['field_clock'],long(100))
   for fraction in range(10,hz+21,10):
    c.write(SLAVE+sy[clock]+4,long(fraction-10));before=c.read(DATA,v.HUNKS[1][2])
    call('timing_scene_begin')
    for slot in range(34,40):
     got=struct.unpack('>3i',c.read(a4+v.A4['position']+slot*12,12))
     want=tuple(p-x+trunc(x*min(fraction,hz),hz) for p,x in zip((10000,20000,30000),(5121,-513,1)))
     require(got==want,('field pose',model,slot,fraction,got,want));samples+=1
    call('timing_scene_end');require(c.read(DATA,v.HUNKS[1][2])==before,'field render leaked')
  return dict(samples=samples,restored=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[dict(model=m,owners=owners(a.build,a.variant,m),poses=poses(a.build,a.variant,m)) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
if __name__=='__main__':main()
