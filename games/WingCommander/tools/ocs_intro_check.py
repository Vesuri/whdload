#!/usr/bin/env python3
"""D4 native 68000/020 scheduler, intro pose restore and owner checks."""
import argparse,json,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import CODE,DATA,word,long
from ocs_reconstruct import new_output,require

def check(build,model):
 c,sy,put,call=setup(build,model)
 results=[]
 try:
  for hz in (50,60):
   for gaps in ((1,),(2,3,7),(150,1,19)):
    put('ocs_clock_hz',hz,4);c.write(DATA+0x77fe,long(0xfffffff0));call('ocs_clock_rebase')
    total=0;elapsed=0;i=0
    while elapsed<hz*10:
     elapsed=min(hz*10,elapsed+gaps[i%len(gaps)]);i+=1
     now=(0xfffffff0+elapsed)&0xffffffff;c.write(DATA+0x77fe,long(now))
     while c.get(SLAVE+sy['ocs_clock_state'],4)!=now:
      call('intro_due');due=c.reg(9);require(due<=4,'batch bound');total+=due
    require(total==100,'equal-time intro ticks')
    require(c.get(SLAVE+sy['ocs_clock_state']+16,4)==0,'dropped debt')
    results.append(dict(hz=hz,gaps=gaps,ticks=total))
  # Original native angular routines run beneath shared prediction; all data
  # hunk bytes, including OCS projection scratch, must restore exactly.
  put('ocs_clock_active',0);put('intro_active',1);put('ocs_clock_hz',50,4)
  c.write(DATA+0x8e8c,bytes(128));c.write(DATA+0x8c54,bytes(128))
  for slot,kind in ((0,4),(1,4),(10,9),(61,0)):
   c.write(DATA+0x8e8c+2*slot,word(kind))
   c.write(DATA+0x8928+12*slot,struct.pack('>iii',1000,2000,3000))
   c.write(DATA+0x94fa+12*slot,struct.pack('>iii',5121,-513,-1))
   for off,vec in ((0x98d6,(0,0,-256)),(0xaa3e,(0,256,0)),(0xad3e,(-256,0,0))):
    c.write(DATA+off+12*slot,struct.pack('>iii',*vec))
   for off in (0x8d06,0x8d86,0x8e06):c.write(DATA+off+slot*2,word(8))
  poses=0
  for view in (0,8,15):
   c.write(DATA+0x3870,word(view));call('timing_scene_snapshot');call('timing_scene_snapshot')
   for pending in (0,1):
    for elapsed in (0,1,4,100):
     c.write(DATA+0x77fe,long(100+elapsed));put('ocs_clock_state',100,4);put('ocs_pending',pending);put('ocs_prediction_cost',0,4)
     before=c.read(DATA,0xf5b8);call('timing_scene_begin')
     fraction=min((elapsed+1+pending)*10,70)
     for slot in (0,1,10,61):
      got=struct.unpack('>iii',c.read(DATA+0x8928+12*slot,12))
      want=tuple(p+int(v*fraction/50) for p,v in zip((1000,2000,3000),(5121,-513,-1)))
      require(got==want,('intro motion',slot,got,want))
     call('timing_scene_end');require(c.read(DATA,0xf5b8)==before,'intro restore');poses+=1
  put('ocs_pending',0)
  # Observe authoritative dispatch; draw wrappers must never allocate asteroids
  # or consume the background-flash timer while intro ownership is active.
  events=[]
  for off,name in ((0x2be,'world'),(0x15d1c,'flash'),(0x290fa,'geometry'),(0x27cfa,'debris'),(0x281c0,'flames'),(0x2837a,'attachments'),(0x9618,'asteroids')):
   def event(name=name):events.append((name,c.get(DATA+0x88de)));c.return_call()
   c.intercept(CODE+off,event)
  put('ocs_prediction_mode',1);c.write(DATA+0x8902,long(1));c.write(DATA+0x88da,word(7));c.write(DATA+0x88de,word(99))
  call('intro_world');require([x[0] for x in events]==['world','flash','geometry','debris','flames','attachments','asteroids'],'world owners')
  require(events[-1][1]==7 and c.get(DATA+0x88de)==99,'asteroid cleanup uses world counter')
  call('ocs_clock_emission');require(c.reg(9)==3,'intro emission uses world counter')
  events.clear();call('ocs_clock_asteroids_draw');call('intro_flash_draw');require(not events,'draw side effects')
  put('intro_active',0);call('ocs_clock_asteroids_draw');call('intro_flash_draw');require([x[0] for x in events]==['asteroids','flash'],'native fallback')
 finally:c.close()
 # Execute the actual shared title loop with a one-field rendering boundary.
 c,sy,put,call=setup(build,model)
 try:
  count=[0];c.write(DATA+0x77fe,long(0))
  def rate():c.return_call(50)
  c.intercept(SLAVE+sy['timing_rate'],rate)
  c.intercept(SLAVE+sy['ocs_publish_drain'],lambda:c.return_call())
  c.intercept(SLAVE+sy['ocs_prediction_snapshot'],lambda:c.return_call())
  def tick():count[0]+=1;c.return_call()
  c.intercept(SLAVE+sy['intro_world'],tick)
  def draw():c.write(DATA+0x77fe,long(c.get(DATA+0x77fe,4)+1));c.return_call()
  c.intercept(SLAVE+sy['intro_draw'],draw)
  c.intercept(SLAVE+sy['intro_finish'],lambda:c.return_call())
  for off in (0x13cc6,0x1ed64,0x1ed9e,0x1efb4,0x180c4):c.intercept(CODE+off,lambda:c.return_call(0))
  c.run(SLAVE-CODE+sy['intro_title'],registers={6:0x1e0000,4:90,15:200,11:0,12:0})
  require(count[0]==296 and c.reg(11)==296 and c.reg(15)==138,('title script',count,c.reg(11),c.reg(15)))
  require(c.get(DATA+0x77fe,4)==1480,'title time')
  require(c.get(SLAVE+sy['intro_active'])==0,'title exit active')
  exits=[]
  for off in (0x1eeb2,0x1f06e):
   def end(off=off):exits.append(off);c.return_call()
   c.intercept(CODE+off,end)
  for skip in (0,1):
   put('intro_active',1);c.run(SLAVE-CODE+sy['intro_credits_end'],registers={12:skip})
   require(c.get(SLAVE+sy['intro_active'])==0,'credit exit active')
  require(exits==[0x1eeb2,0x1f06e],'credit exit routes')
 finally:c.close()
 # Execute the unchanged native credit field comparisons at both boundaries.
 c,sy,put,call=setup(build,model)
 try:
  hits=[]
  for off in (0x1f016,0x1f036,0x1effc,0x1f05a):
   def hit(off=off):hits.append(off);c.return_call()
   c.intercept(CODE+off,hit)
  for entry,elapsed,want in ((0x1f008,219,0x1f016),(0x1f008,220,0x1f036),(0x1f04c,319,0x1effc),(0x1f04c,320,0x1f05a)):
   c.write(DATA+0x77fe,long(1000+elapsed));c.run(entry,registers={13:1000})
   require(hits[-1]==want,'native credit deadline')
 finally:c.close()
 return dict(schedules=results,pose_cases=poses,title_ticks=296,title_fields=1480,owners=True,exits=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 result={str(m):check(a.build,m) for m in (1,2)}
 (out/'report.json').write_text(json.dumps(dict(passed=True,models=result),indent=2)+'\n')
 print('OCS intro scheduler, title, prediction, restoration and owners pass on 68000/020')
if __name__=='__main__':main()
