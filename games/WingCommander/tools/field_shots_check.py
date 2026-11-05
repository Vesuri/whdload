#!/usr/bin/env python3
"""Bounded native swept field collision and presentation regression.

Synthetic geometry, real native radius query and renderer; no performance claim.
"""
import argparse,json,struct,random,math
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import DATA,CODE,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output,require
from variants import get


def check(build,variant,model):
 c,sy=machine(build,variant,model);v=get(variant);a4=DATA+v.A4_BASE;o=variant=='ocs'
 kind=a4+v.A4['object_class'];pos=a4+v.A4['position'];vel=a4+v.A4['velocity'];rad=a4+(0x128a if o else 0x1afc)
 models=a4+(0xf86 if o else 0x17f8);owner=a4+(0x3058 if o else 0x3a6a)
 clock='ocs_clock_state' if o else 'timing_clock'
 def vec(base,slot,xyz):c.write(base+slot*12,struct.pack('>3i',*xyz))
 def readpos(slot):return struct.unpack('>3i',c.read(pos+slot*12,12))
 def put(n,x,size=2):c.write(SLAVE+sy[n],word(x) if size==2 else long(x))
 def run(n,args=b''):c.run(SLAVE-CODE+sy[n],args)
 def cache(slot=10):return c.read(SLAVE+sy['field_shot_targets']+slot,1)[0]
 def native(slot=10):c.run(0x156e6 if o else 0x1597e,word(slot));return c.reg(9)&65535
 def query(slot=10):run('field_shot_query',word(slot));return c.reg(9)&65535
 def setup(hazard=9,offset=0,speed=200*256):
  c.write(kind,bytes(128));c.write(a4+(-18318 if o else -18280),word(0));c.write(a4+(-29954 if o else -29978),word(0))
  for slot,k,m in ((0,12,0),(10,8,24),(34,hazard,33 if hazard==10 else 34)):
   c.write(kind+slot*2,word(k));c.write(models+slot*2,word(m));c.write(rad+slot*2,word(10 if slot==10 else 100))
   c.write(a4+(0xcf4 if o else 0x1566)+slot*2,word(-1));c.write(a4+(0xc56 if o else 0x14c8)+slot*2,word(-1))
   for off,xyz in zip(((0x18d8,0x2a40,0x2d40) if o else (0x214a,0x3452,0x3752)),((0,0,256),(0,256,0),(256,0,0))):vec(a4+off,slot,xyz)
   vec(pos,slot,(0,0,0) if slot==0 else (offset,0,100000+200*256) if slot==10 else (0,0,100000))
   vec(vel,slot,(0,0,400*256) if slot==10 else (speed,0,0) if slot==34 else (0,0,0))
  c.write(owner+10,b'\0');put('ocs_clock_active' if o else 'timing_active',1);put('intro_active',0)
  if o:put('ocs_prediction_cost',0,4)
  put('ocs_clock_hz' if o else 'timing_hz',50,4);put(clock,100,4);c.write(a4+v.A4['field_clock'],long(100))
  run('timing_scene_snapshot');run('timing_scene_snapshot')
 try:
  # Independent Euclidean closest-point oracle with a wide margin around the
  # native approximate metric/normalization boundary. Axis cases test boundary.
  rng=random.Random(19);geometry=0
  for _ in range(180):
   r=[rng.randrange(-500000,500001) for _ in range(3)];d=[rng.randrange(-1000000,1000001) for _ in range(3)];radius=100000
   denom=sum(x*x for x in d);t=max(0,min(1,-sum(x*y for x,y in zip(r,d))/denom)) if denom else 0
   distance=math.sqrt(sum((x+t*y)**2 for x,y in zip(r,d)))
   if abs(distance-radius)<radius*.02:continue
   c.write(SLAVE+sy['field_segment'],struct.pack('>6i',*(r+d)));put('field_radius',radius//256*256,4)
   run('field_segment_hit');got=c.reg(9)
   require((got!=0xffffffff)==(distance<radius),('sweep geometry',r,d,distance,got))
   if got!=0xffffffff:
    point=[x+math.trunc(y*got/65536) for x,y in zip(r,d)]
    require(math.sqrt(sum(x*x for x in point))<radius*1.01,('entry',got,point))
   geometry+=1
  rows=[]
  for hazard in (9,10):
   for speed in (0,200*256,-200*256):
    # Aim at the moving target's midpoint, with both endpoints outside radius.
    setup(hazard,-speed//2,speed)
    require(native()==65535,'fixture must tunnel under original endpoint query')
    require(cache()==34,('swept target',hazard,speed,cache()))
    t=c.get(SLAVE+sy['field_shot_fractions']+40,4)
    require(0<t<65536,('entry fraction',t))
    samples=0
    for hz in (50,60):
     put('ocs_clock_hz' if o else 'timing_hz',hz,4)
     for f in range(10,hz+21,10):
      c.write(SLAVE+sy[clock]+4,long(f-10));before=c.read(DATA,v.HUNKS[1][2]);run('timing_scene_begin')
      fraction=min(f,hz)/hz
      wantx=math.trunc(-speed+speed*fraction)
      require(abs(readpos(34)[0]-wantx)<=1,('hazard interval',speed,hz,f,readpos(34)))
      if f*65536>=t*hz:
       contact=struct.unpack('>3i',c.read(SLAVE+sy['field_shot_contacts']+120,12))
       require(tuple(x-y for x,y in zip(readpos(10),readpos(34)))==contact,'bolt passed displayed contact')
      run('timing_scene_end');require(c.read(DATA,v.HUNKS[1][2])==before,'presentation leaked');samples+=1
    before=c.read(DATA,v.HUNKS[1][2]);require(query()==34,'swept query failed')
    require(cache()==255,'contact not consumed');require(c.read(SLAVE+sy['field_shot_effects']+10,1)==b'\1','impact not marked')
    # Native response receives the corresponding collision vector and position.
    rel=struct.unpack('>3i',c.read(a4+(0x3128 if o else 0x3b3a),12))
    require(tuple(x-y for x,y in zip(readpos(10),readpos(34)))==rel,'response position mismatch')
    rows.append(dict(hazard=hazard,speed=speed,fraction=t,samples=samples))
  # Real collision response, native model-51 initialization and integration.
  # Pin only RNG to its non-breakup branch; asset-independent game code runs.
  c.write(CODE+(0x7f1a if o else 0x81a4),word(0x4eb9)+long(SLAVE+sy['field_shot_query']))
  random_result=[1]
  c.intercept(CODE+(0x2bbe6 if o else 0x2cb70),lambda:c.return_call(random_result[0]))
  for hazard in (9,10):
   setup(hazard,speed=0)
   c.run(0x7f0c if o else 0x8196,word(10))
   require(c.get(kind+20)==5 and c.get(models+20)==51,('native impact effect',hazard,c.get(kind+20),c.get(models+20)))
   # Mirror the following linear integration only, then execute real snapshot.
   effect=readpos(10);step=(768,-256,512)
   vec(vel,10,step);vec(pos,10,tuple(x+y for x,y in zip(effect,step)))
   run('timing_scene_snapshot')
   require(c.read(SLAVE+sy['timing_scene_predictable']+10,1)==b'\1','first impact interval not certified')
   put('ocs_clock_hz' if o else 'timing_hz',50,4);c.write(SLAVE+sy[clock]+4,long(0))
   before=c.read(DATA,v.HUNKS[1][2]);run('timing_scene_begin')
   require(readpos(10)==tuple(x+math.trunc(y/5) for x,y in zip(effect,step)),'impact phase jump')
   run('timing_scene_end');require(c.read(DATA,v.HUNKS[1][2])==before,'effect render leaked')
  # Exercise the native asteroid-breakup branch too; destruction remains RNG-owned.
  setup(speed=0);random_result[0]=0
  c.run(0x7f0c if o else 0x8196,word(10))
  require(c.get(kind+20)==5 and c.get(kind+68)!=9,'native asteroid breakup not reached')
  random_result[0]=1
  # Miss / original / AI / cinematic / stale target / reuse / nearer target.
  setup(offset=300*256,speed=0);require(cache()==255 and query()==65535,'near miss hit')
  for mode in ('off','intro','ai','moved','model','dead','reused'):
   setup(speed=0)
   if mode=='off':put('ocs_clock_active' if o else 'timing_active',0)
   elif mode=='intro':put('intro_active',1)
   elif mode=='ai':c.write(owner+10,b'\1')
   elif mode=='moved':vec(pos,34,(1000000,0,100000))
   elif mode=='model':c.write(models+68,word(38))
   elif mode=='dead':c.write(kind+68,word(0))
   elif mode=='reused':c.write(SLAVE+sy['field_shot_targets']+10,b'\xff')
   require(query()==65535,('excluded',mode))
  setup(speed=0)
  # New lower-index target lies later along the segment: earliest contact wins.
  for base,size in ((kind,2),(models,2),(rad,2),(pos,12),(vel,12)):
   c.write(base+20*size,c.read(base+34*size,size))
  vec(pos,20,(0,0,100000+100*256));run('timing_scene_snapshot');run('timing_scene_snapshot')
  require(cache()==34,'slot order replaced chronological order')
  # A native ship endpoint keeps priority over an earlier field crossing.
  setup(speed=0);c.write(kind+2,word(12));c.write(rad+2,word(100));vec(pos,1,readpos(10))
  run('timing_scene_snapshot');require(cache()==255 and query()==1,'non-field native priority')
  # Negative controls: remove cache for tunnelling; remove display limiter.
  setup(speed=0);c.write(SLAVE+sy['field_shot_targets']+10,b'\xff');require(query()==65535,'tunnelling control blind')
  setup(speed=0);address=SLAVE+sy['field_shot_limit'];saved=c.read(address,2);c.write(address,word(0x4e75))
  c.write(SLAVE+sy[clock]+4,long(40));run('timing_scene_begin');require(readpos(10)[2]>readpos(34)[2]+110*256,'display control blind');run('timing_scene_end');c.write(address,saved)
  return dict(model=model,geometry=geometry,contacts=rows,negative_controls=True,exclusions=True,native_response=True,first_impact_interval=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
if __name__=='__main__':main()
