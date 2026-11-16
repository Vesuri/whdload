#!/usr/bin/env python3
"""TrainSim enemy-info pacing: the original E:17d06 / O:17498 loop with the slave's hooks.

From pass INFO_BETWEEN on, each pass also publishes a picture between it and the
next, one degree on: the pass's picture waits 2 fields from its slot and the one
between ends the slot. The expected field of every picture comes from that policy
simulated here, with drawing taking 0, 1 or 5 fields per picture.

CD32 also: every pass's native publish runs with modal_info_changed set (the
changed-block converter takes it), the flag is clear between passes, and the
converter's destination records survive until the last pass and are dropped after it."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_clock_check import SLAVE
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_reconstruct import ROOT,new_output,require
from variants import get
from modal_source import specification,INFO_LIMIT,INFO_BETWEEN

# Routine span, publish call site, native publish, pass count, first full-detail pass.
SPAN=dict(cd32=(0x17d06,0x1804e,0x1802c,0x31fc2,63,42),ocs=(0x17498,0x177e0,0x177be,0x3260a,70,49))
ANGLE=dict(cd32=-30050,ocs=-30026)    # A4 offset of the ship angle the pass steps


def expected(passes,period,gap):
 """Field of every picture, whether it is a picture between, and the field the last slot ends."""
 field=1000;cursor=field;out=[]
 for d2 in range(passes):
  for between in ((False,True) if d2>=INFO_BETWEEN else (False,)):
   out.append((field,between));field+=gap
   if d2>=INFO_BETWEEN and not between:
    field=max(field,cursor+2)
   else:
    field=max(field,cursor+period);cursor+=period
 return out,field


def check(build,variant,model):
 v=get(variant);s=SLAVE;ocs=variant=='ocs'
 if ocs:c,sy,_,_=setup(build,model)
 else:
  c=Native(ROOT/v.GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(s,(build/'payload.bin').read_bytes());c.write(s+sy['timing_game'],long(CODE))
 start,end,site,publish,passes,full=SPAN[variant]
 field=DATA+v.A4_BASE+v.A4['field_clock'];hz='ocs_clock_hz' if ocs else 'timing_hz'
 try:
  require(any(off==site and label=='modal_info_publish' for off,_,label in specification(variant)[5]),'publish site not specified')
  original=c.read(CODE+start,end-start)
  c.run(s-CODE+sy['modal_install'],registers={1:CODE})
  require(c.read(CODE+site,6)==word(0x4eb9)+long(s+sy['modal_info_publish']),'publish hook not installed')
  if ocs:require(c.get(CODE+0x177d2)==70,'OCS pass limit changed')
  else:require(c.get(CODE+INFO_LIMIT[0])==INFO_LIMIT[2]==63,'CD32 hold not installed')
  # Stub every drawing call in the loop; only presentation timing is checked.
  targets=set()
  for at in range(start,end-6,2):
   op=struct.unpack_from('>H',original,at-start)[0]
   if op==0x4eb9:t=struct.unpack_from('>I',original,at-start+2)[0]
   elif op==0x4eba:t=at+2+struct.unpack_from('>h',original,at-start+2)[0]+CODE
   else:continue
   if at!=site and t-CODE not in (0x17aea,0x1727c):targets.add(t)
  for t in targets:c.intercept(t,lambda:c.return_call())
  state=dict(gap=0,period=3,pictures=[],flags=[],kept=[],angles=[])
  angle=DATA+v.A4_BASE+ANGLE[variant]
  flag=None if ocs else s+sy['modal_info_changed'];dest=None if ocs else s+sy['flight_destinations']
  def shown():
   state['pictures'].append(c.get(field,4));state['angles'].append(c.get(angle,2))
   if not ocs:state['flags'].append(c.get(flag,2));state['kept'].append(c.read(dest,8)==bytes(range(1,9)))
   c.write(field,long(c.get(field,4)+state['gap']));c.return_call()
  c.intercept(CODE+publish,shown)
  def idle():
   # Time passes only while the slave actually waits for the next slot.
   if not ocs:require(c.get(flag,2)==0,'changed-block flag left set while waiting')
   due=c.get(s+sy['modal_info_cursor'],4)+state['period']
   if c.get(field,4)<due:c.write(field,long(c.get(field,4)+1))
  c.intercept(s+sy["modal_info_idle"],idle)
  def first():
   if not ocs:require(c.get(flag,2)==0,'changed-block flag left set while waiting')
   if c.get(field,4)<c.get(s+sy['modal_info_cursor'],4)+2:c.write(field,long(c.get(field,4)+1))
  c.intercept(s+sy["modal_info_first"],first)
  rows=[]
  for rate in (50,60):
   for gap in (0,1,5):
    period=3 if rate==50 else 4
    c.write(s+sy[hz],long(rate));c.write(field,long(1000));state.update(gap=gap,period=period,pictures=[],flags=[],kept=[],angles=[])
    c.write(0x1a0000,bytes(256))
    if not ocs:c.write(dest,bytes(range(1,9)))
    c.run(start,long(0x1a0000)+word(1))
    want,end=expected(passes,period,gap);p=state['pictures'];n=len(want)
    require(len(p)==n,('pictures',rate,gap,len(p),n))
    require(p==[f for f,_ in want],('cadence',rate,gap,[b-a for a,b in zip(p,p[1:])][:40]))
    # Two degrees a pass before INFO_BETWEEN, one degree a picture from it.
    turns=[(b-a)%360 for a,b in zip(state['angles'],state['angles'][1:])]
    require(turns==[2 if i<INFO_BETWEEN else 1 for i in range(len(turns))],('angle steps',turns[:40]))
    if not ocs:
     require(state['flags']==[1]*n,('changed-block flag during publish',state['flags'][:8]))
     require(all(state['kept']),'destination records dropped before the last picture')
     require(c.get(flag,2)==0 and c.read(dest,8)==bytes(8),'flag or destination records left after the last picture')
    hold=end-[f for f,b in want if not b][full]
    rows.append(dict(hz=rate,draw_fields=gap,passes=passes,pictures=n,fields=end-p[0],detail_hold_fields=hold))
  return dict(model=model,cases=rows)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,models=rows),indent=2)+'\n')
 print('PASS:',a.variant,json.dumps(rows[0]['cases'][0]),json.dumps(rows[0]['cases'][3]))
if __name__=='__main__':main()
