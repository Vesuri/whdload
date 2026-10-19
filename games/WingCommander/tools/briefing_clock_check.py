#!/usr/bin/env python3
"""Compare native crowd loops with three-field pacing; mock graphics and IRQs."""
import argparse,json
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE,DATA,STOP,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output
from variants import get


def check(build,variant,model):
 c,sy=machine(build,variant,model);v=get(variant);ocs=variant=='ocs'
 base=DATA+v.A4_BASE;field=base+v.A4['field_clock'];state={};rows=[]
 entries=(0x23060,0x23284,0x1c3f6) if ocs else (0x23ec2,0x240e6,0x1d120)
 ends=(0x230f8,0x23364,0x1c484) if ocs else (0x23f5a,0x241c6,0x1d1ae)
 def advance(n):c.write(field,long((c.get(field,4)+n)&0xffffffff))
 def publish():state['pictures']+=1;advance(state['gap']);c.return_call()
 def bitmap():state['bitmaps'].append(c.read(c.reg(8)+4,14).hex());c.return_call()
 def actor():state['actors'].append(c.read(c.reg(8)+4,10).hex());c.return_call()
 def wait():
  if (c.get(field,4)-c.get(SLAVE+sy['modal_crowd_cursor'],4))&0xffffffff<3:advance(1)
 try:
  for off in ((0x31edc,) if ocs else (0x318d2,)):c.intercept(CODE+off,lambda:c.return_call())
  c.intercept(CODE+(0x2f9a6 if ocs else 0x2efe8),bitmap)
  c.intercept(CODE+(0x24392 if ocs else 0x251ec),actor)
  c.intercept(CODE+(0x2cbd0 if ocs else 0x2cb70),lambda:c.return_call(0))
  c.intercept(CODE+(0x180c4 if ocs else 0x1898a),lambda:c.return_call(1 if state['skip'] else 0))
  c.intercept(CODE+(0x146b0 if ocs else 0x14d12),lambda:c.return_call())
  for off in ((0x3260a,0x2de) if ocs else (0x31fc2,0x2dc)):c.intercept(CODE+off,publish)
  for off in ends:c.intercept(CODE+off,lambda:c.reg(18,STOP))
  c.intercept(SLAVE+sy['modal_crowd_wait'],wait)
  # IRQ advances on every wait-loop visit (the body starts after MOVEM).
  c.intercept(SLAVE+sy['modal_crowd_wait']+4,wait)
  table=base+(-0x52b2 if ocs else -0x528e)
  for i in range(14):
   c.write(table+20*i+14,long(0x180000));c.write(0x180000,bytes(range(22)))
  initial=c.read(DATA,v.HUNKS[1][2])
  def run(stage,gap=1,start=100,skip=False):
   c.write(DATA,initial);c.write(field,long(start));c.write(0x170000-42,bytes(42))
   state.clear();state.update(gap=gap,skip=skip,pictures=0,bitmaps=[],actors=[])
   c.run(entries[stage],registers={6:0x170000,13:0,14:0,15:0})
   return dict(pictures=state['pictures'],bitmaps=state['bitmaps'][:],actors=state['actors'][:],fields=(c.get(field,4)-start)&0xffffffff,sp=c.reg(8))
  native=[run(i) for i in range(3)]
  assert [x['pictures'] for x in native]==[22,40,22],native
  c.run(SLAVE-CODE+sy['modal_install'],registers={1:CODE})
  for stage in range(3):
   for gap in (1,9):
    for start in (100,0xfffffff0):
     got=run(stage,gap,start);ref=native[stage]
     for k in ('pictures','bitmaps','actors','sp'):assert got[k]==ref[k],(stage,k)
     assert got['fields']==ref['pictures']*max(3,gap),(stage,got['fields'])
     rows.append(dict(stage=stage,gap=gap,start=start,fields=got['fields']))
   got=run(stage,skip=True)
   assert got['pictures']==(22 if stage==2 else 1),got
   assert run(stage)['fields']==native[stage]['pictures']*3
  return dict(model=model,schedules=rows,skip_and_reentry=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser();p.add_argument('variant',choices=('cd32','ocs'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(passed=True,results=rows),indent=2)+'\n');print('PASS',a.variant,'crowd frames, three-field cadence, wrap, overrun, skip and re-entry')
if __name__=='__main__':main()
