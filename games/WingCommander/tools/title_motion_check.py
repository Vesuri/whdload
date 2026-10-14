#!/usr/bin/env python3
"""Native render-only title scale/rotation sampling, including fractional depth."""
import argparse,json,re
from pathlib import Path
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_reconstruct import ROOT,new_output,require
from variants import get


def check(build,variant,model):
 v=get(variant);slave=0x500000
 if variant=='ocs':
  sy=json.loads((build/'build.json').read_text())['symbols'];blob=(build/'WingCommander.Slave').read_bytes()[32:-4]
  clock,rate='ocs_clock_state','ocs_clock_hz'
 else:
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  blob=(build/'payload.bin').read_bytes();clock,rate='timing_clock','timing_hz'
 c=Native(ROOT/'tmp/originals/ocs/WingCommander/data/Wing.english',model)
 try:
  c.write(slave,blob);cases=0;examples={}
  for hz in (50,60):
   c.write(slave+sy[rate],long(hz))
   for tick,depth,angle in ((134,200,0),(135,200,0),(180,20,0),(200,16,0),(234,16,0),(235,16,0),(260,66,150)):
    scales=[];angles=[]
    for elapsed in range(hz//10+1):
     for origin in (100,0xfffffffe):
      for debt in (0,10):
       c.write(slave+sy[clock],long(origin));c.write(slave+sy[clock]+4,long(debt))
       c.write(DATA+v.A4_BASE+v.A4['field_clock'],long(origin+elapsed))
       c.write(0x1dfffe,word(angle))
       regs={6:0x1e0000,11:tick,12:0x12345678,13:0xabc,14:0xdef,15:depth}
       before=c.read(0x1dfffe,2)
       c.run(slave-CODE+sy['intro_title_sample'],registers=regs)
       f=min(hz,elapsed*10+debt)
       denominator=depth*hz
       if 135<=tick<235 and depth>16:denominator-=4*f
       elif tick>=235:denominator+=2*f
       scale=4096*hz//denominator
       rotation=angle+(6*f//hz if tick>=235 else 0)
       require(c.reg(9)==scale and c.reg(10)&65535==rotation,'fractional title projection/rotation')
       require(all(c.reg(r)==x for r,x in regs.items()) and c.read(0x1dfffe,2)==before,'authoritative title state changed')
       cases+=1
       if origin==100 and debt==0:scales.append(scale);angles.append(rotation)
    if tick==180:
     require(len(set(scales))>2,'approach still steps at tick boundaries')
     examples[str(hz)+'-approach']=scales
    if tick==235:
     require(len(set(angles))==hz//10+1,'rotation still steps at tick boundaries')
     examples[str(hz)+'-departure-scale']=scales;examples[str(hz)+'-rotation']=angles
  return dict(model=model,cases=cases,examples=examples)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 result=dict(passed=True,variant=a.variant,models=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))])
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
