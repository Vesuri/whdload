#!/usr/bin/env python3
"""TrainSim enemy-info pacing: the original E:17d06 / O:17498 loop with the slave's hooks.

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
from modal_source import specification,INFO_LIMIT

# Routine span, publish call site, native publish, pass count, first full-detail pass.
SPAN=dict(cd32=(0x17d06,0x1804e,0x1802c,0x31fc2,63,42),ocs=(0x17498,0x177e0,0x177be,0x3260a,70,49))


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
  state=dict(gap=0,period=3,pictures=[],flags=[],kept=[])
  flag=None if ocs else s+sy['modal_info_changed'];dest=None if ocs else s+sy['flight_destinations']
  def shown():
   state['pictures'].append(c.get(field,4))
   if not ocs:state['flags'].append(c.get(flag,2));state['kept'].append(c.read(dest,8)==bytes(range(1,9)))
   c.write(field,long(c.get(field,4)+state['gap']));c.return_call()
  c.intercept(CODE+publish,shown)
  def idle():
   # Time passes only while the slave actually waits for the next slot.
   if not ocs:require(c.get(flag,2)==0,'changed-block flag left set while waiting')
   due=c.get(s+sy['modal_info_cursor'],4)+state['period']
   if c.get(field,4)<due:c.write(field,long(c.get(field,4)+1))
  c.intercept(s+sy["modal_info_idle"],idle)
  rows=[]
  for rate in (50,60):
   for gap in (0,1,5):
    period=3 if rate==50 else 4
    c.write(s+sy[hz],long(rate));c.write(field,long(1000));state.update(gap=gap,period=period,pictures=[],flags=[],kept=[])
    c.write(0x1a0000,bytes(256))
    if not ocs:c.write(dest,bytes(range(1,9)))
    c.run(start,long(0x1a0000)+word(1))
    if not ocs:
     require(state['flags']==[1]*passes,('changed-block flag during publish',state['flags'][:8]))
     require(all(state['kept']),'destination records dropped before the last pass')
     require(c.get(flag,2)==0 and c.read(dest,8)==bytes(8),'flag or destination records left after the last pass')
    p=state['pictures'];deltas=[b-a for a,b in zip(p,p[1:])]
    require(len(p)==passes,('passes',rate,gap,len(p)))
    require(p[0]==1000,('first pass waited',p[0]))
    # Fixed cadence from the first pass; drawing slower than it retains debt.
    require(all(d==max(period,gap) for d in deltas),('cadence',rate,gap,deltas[:8]))
    hold=(passes-full)*max(period,gap)
    rows.append(dict(hz=rate,draw_fields=gap,passes=len(p),fields=p[-1]-p[0]+max(period,gap),detail_hold_fields=hold))
  return dict(model=model,cases=rows)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,models=rows),indent=2)+'\n')
 print('PASS:',a.variant,json.dumps(rows[0]['cases'][0]),json.dumps(rows[0]['cases'][3]))
if __name__=='__main__':main()
