#!/usr/bin/env python3
"""Native intro impact endpoints, display lead and authoritative isolation."""
import argparse,json,struct
from pathlib import Path
from field_objects_check import machine
from ocs_clock_check import SLAVE
from ocs_display_check import DATA,word,long,CODE
from ocs_reconstruct import new_output,require
from variants import get
from timing_scene_check import trunc


def check(build,variant,model):
 c,sy=machine(build,variant,model);v=get(variant);a4=DATA+v.A4_BASE;ocs=variant=='ocs'
 pos=a4+v.A4['position'];vel=a4+v.A4['velocity'];kind=a4+v.A4['object_class']
 radius=a4+(0x128a if ocs else 0x1afc);owner=a4+(0x3058 if ocs else 0x3a6a)
 models=a4+(0xf86 if ocs else 0x17f8);action=a4+(0xcf4 if ocs else 0x1566)
 clock='ocs_clock_state' if ocs else 'timing_clock';hzname='ocs_clock_hz' if ocs else 'timing_hz'
 def put(n,x,size=2):c.write(SLAVE+sy[n],word(x) if size==2 else long(x))
 def run(n):c.run(SLAVE-CODE+sy[n])
 def vector(base,slot,xyz):c.write(base+slot*12,struct.pack('>3i',*xyz))
 def readpos(slot):return struct.unpack('>3i',c.read(pos+slot*12,12))
 cases=0;clips=0
 try:
  put('ocs_clock_active' if ocs else 'timing_active',0);put('intro_active',1)
  if ocs:put('ocs_prediction_cost',0,4)
  c.write(a4+(-18318 if ocs else -18280),word(15));c.write(kind,bytes(128))
  for slot,k in ((1,12),(4,12),(10,8),(11,8)):
   c.write(kind+slot*2,word(k));c.write(models+slot*2,word(10 if k==12 else 24))
   c.write(radius+slot*2,word(100 if k==12 else 10))
   c.write(action+slot*2,word(9)) if slot<10 else None
   vector(vel,slot,(0,0,2560 if slot<10 else -48640))
   for off,vec in zip(((0x18d8,0x2a40,0x2d40) if ocs else (0x214a,0x3452,0x3752)),((0,0,256),(0,256,0),(256,0,0))):vector(a4+off,slot,vec)
   for off in ((0xd08,0xd88,0xe08) if ocs else (0x157a,0x15fa,0x167a)):c.write(a4+off+slot*2,word(0))
  c.write(owner+10,b'\x04');c.write(owner+11,b'\x04')
  vector(pos,4,(1000000,0,0));vector(pos,11,(1000000,0,1000000))
  for contact,z in ((0,50*256),(1,250*256),(-1,1000*256)):
   vector(pos,1,(0,0,0));vector(pos,10,(0,0,z))
   put('timing_scene_valid',0)
   before=c.read(DATA,v.HUNKS[1][2]);run('timing_scene_snapshot');run('timing_scene_snapshot')
   require(c.read(DATA,v.HUNKS[1][2])==before,'contact query leaked native scratch/pose')
   target=c.read(SLAVE+sy['timing_intro_shot_targets']+10,1)[0]
   require(target==(255 if contact<0 else 1),('native contact',contact,target))
   if contact>=0:require(c.read(SLAVE+sy['timing_intro_shot_steps']+10,1)[0]==contact,'contact time')
   for hz in (50,60):
    put(hzname,hz,4);put(clock,100,4);c.write(a4+v.A4['field_clock'],long(100))
    for fraction in range(10,hz+21,10):
     c.write(SLAVE+sy[clock]+4,long(fraction-10));before=c.read(DATA,v.HUNKS[1][2])
     run('timing_scene_begin')
     if contact>=0 and fraction>contact*hz:
      want=(0,0,z-51200*contact+trunc(2560*fraction,hz));clips+=1
     else:want=(0,0,z+trunc(-48640*fraction,hz))
     require(readpos(10)==want,('impact endpoint',model,contact,hz,fraction,readpos(10),want))
     require(readpos(11)==(1000000,0,1000000+trunc(-48640*fraction,hz)),'unrelated shot changed')
     run('timing_scene_end');require(c.read(DATA,v.HUNKS[1][2])==before,'render leaked')
     cases+=1
  # Removing only the limiter restores the reported through-target forecast.
  vector(pos,1,(0,0,0));vector(pos,10,(0,0,50*256))
  run('timing_scene_snapshot');run('timing_scene_snapshot')
  put(hzname,50,4);c.write(SLAVE+sy[clock]+4,long(60))
  address=SLAVE+sy['timing_intro_shot_limit'];saved=c.read(address,2)
  c.write(address,word(0x4e75));before=c.read(DATA,v.HUNKS[1][2])
  run('timing_scene_begin')
  require(readpos(10)[2]<readpos(1)[2],'uncapped negative control did not pass target')
  run('timing_scene_end');require(c.read(DATA,v.HUNKS[1][2])==before,'control render leaked')
  c.write(address,saved)
  # Native response ignores the shooter; non-intro flight must not be clipped.
  vector(pos,10,(1000000,0,50*256));run('timing_scene_snapshot')
  require(c.read(SLAVE+sy['timing_intro_shot_targets']+10,1)==b'\xff','self contact')
  vector(pos,10,(0,0,50*256));put('intro_active',0);run('timing_scene_snapshot')
  require(c.read(SLAVE+sy['timing_intro_shot_targets'],64)==b'\xff'*64,'flight contact policy changed')
  return dict(model=model,samples=cases,limited=clips,native_query_restored=True,render_restored=True)
 finally:c.close()


def replay(build,capture):
 """Actual CD32 native world updates from the original title capture."""
 import re
 from timing_audit_check import CPU
 from cd32_runtime import locate
 memory=capture.read_bytes();s=0x180000
 sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
 c=CPU(memory,locate(memory),2);c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],struct.pack('>I',c.code));c.write(c.code+0x807a,struct.pack('>HI',0x4ef9,s+sy['translation_velocity']))
 def put(n,x,size=2):c.write(s+sy[n],x.to_bytes(size,'big'))
 def run(n):c.run(s+sy[n]-c.code)
 put('intro_active',1);put('timing_hz',50,4);rows=[];pending=[];impacts=0
 try:
  for tick in range(100):
   c.run(0x2a8)
   for slot in pending:
    require(c.data_value(0x96fe+2*slot,'h')==5 and c.data_value(0x97f6+2*slot,'h')==51,'predicted contact did not become native impact')
    impacts+=1
   run('timing_scene_snapshot');base=c.read(c.data,0xfda0)
   limits=[]
   for slot in range(10,61):
    target=c.read(s+sy['timing_intro_shot_targets']+slot,1)[0]
    if target<10:limits.append((slot,target,c.read(s+sy['timing_intro_shot_steps']+slot,1)[0]))
   for fraction in (10,30,50,70):
    put('timing_clock',100,4);c.data_value(0x7f02,'I',100);c.write(s+sy['timing_clock']+4,struct.pack('>I',fraction-10));base=c.read(c.data,0xfda0)
    run('timing_scene_begin')
    for slot,target,step in limits:
     if fraction>step*50:
      def vec(raw,off,i):return struct.unpack_from('>3i',raw,off+12*i)
      shown=c.read(c.data,0xfda0)
      rel=tuple(a-b for a,b in zip(vec(shown,0x919a,slot),vec(shown,0x919a,target)))
      want=tuple(a-b+step*(v-w) for a,b,v,w in zip(vec(base,0x919a,slot),vec(base,0x919a,target),vec(base,0x9d6c,slot),vec(base,0x9d6c,target)))
      assert rel==want,(tick,slot,target,step,fraction,rel,want)
    run('timing_scene_end');assert c.read(c.data,0xfda0)==base
   pending=[slot for slot,target,step in limits if step==0]
   if limits:rows.append(dict(tick=tick,limits=limits))
  require(len(rows)>=8 and impacts==8,'native intro did not exercise four impact volleys')
  return dict(ticks=100,samples=400,native_impacts=impacts,limited=rows,authoritative_restored=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('cd32','ocs'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 p.add_argument('--native-intro-capture',type=Path,help='original CD32 title-animation-fast.bin for native world replay')
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 r=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 result=dict(passed=True,variant=a.variant,models=r)
 if a.native_intro_capture:
  require(a.variant=='cd32','native replay capture is CD32')
  result['native_intro']=replay(a.build,a.native_intro_capture)
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(r)
if __name__=='__main__':main()
