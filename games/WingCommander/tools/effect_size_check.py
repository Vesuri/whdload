#!/usr/bin/env python3
"""Compare fractional effect sizes with the original script interpreter."""
import argparse,json,re,struct
from pathlib import Path
from ocs_prediction_check import setup
from ocs_display_check import Native,CODE,DATA,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import ROOT,new_output,require
from variants import get
from timing_scene_check import trunc


def check(build,variant,model):
 ocs=variant=='ocs'
 if ocs:c,sy,_,_=setup(build,model)
 else:
  c=Native(ROOT/get(variant).GAME,model=model,variant=variant)
  sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
  c.write(SLAVE,(build/'payload.bin').read_bytes());c.write(SLAVE+sy['timing_game'],long(CODE))
 a4=DATA+0x7ffe;slot=10;script=0x190000
 kind,mod,size,period,cursor,table=(0xe8e,0xf86,0x29ba,0x3666,0x36e6,-11224) if ocs else (0x1700,0x17f8,0x33cc,0x4078,0x40f8,-11354)
 sizeaddr=a4+size+slot*2;data_size=0xf5b8 if ocs else 0xfda0
 def run(n,regs=None):c.run(SLAVE-CODE+sy[n],registers=regs)
 def put(n,v,sz=2):c.write(SLAVE+sy[n],word(v) if sz==2 else long(v))
 count=0
 try:
  c.write(a4+kind,bytes(128));c.write(a4+mod+slot*2,word(0))
  c.write(a4+table+26,long(script));c.write(a4+table+36,word(1))
  removed=[]
  c.intercept(CODE+(0x29026 if ocs else 0x29fb2),lambda:(removed.append(True),c.return_call()))
  for k in (5,6,9,10):
   c.write(a4+kind+slot*2,word(k))
   for initial in (63,64,1024,32768,65535):
    for delay in (-32768,0,1,2):
     for commands in ((0x406,), (0x803,), (3,), (0xa000,), (0x9001,0x406), (0x9001,0x803), (0,0x406), (0x406,0x803), (0x406,0xa000)):
      c.write(script,struct.pack('>'+len(commands)*'H',*commands)+word(0)+word(0))
      c.write(sizeaddr,word(initial));c.write(a4+period+slot*2,word(delay));c.write(a4+cursor+slot*2,word(0))
      before=c.read(DATA,data_size)
      c.run(0x2800a if ocs else 0x28f96,word(slot))
      endpoint=c.get(sizeaddr)
      if commands[0]!=0xa000:
       c.run(0x2800a if ocs else 0x28f96,word(slot))
      second=c.get(sizeaddr);c.write(DATA,before)
      for hz in (50,60):
       for fraction in (0,10,hz-10,hz,hz+20):
        run('timing_scene_effect_size',{13:slot,15:fraction,16:hz})
        expected=(initial+trunc((endpoint-initial)*fraction,hz) if fraction<=hz else
                  endpoint+trunc((second-endpoint)*(fraction-hz),hz))
        require(c.get(sizeaddr)==expected,('size',k,initial,delay,commands,hz,fraction,c.get(sizeaddr),endpoint))
        after=bytearray(c.read(DATA,data_size));after[sizeaddr-DATA:sizeaddr-DATA+2]=word(initial)
        require(bytes(after)==before,'preview changed script state')
        c.write(sizeaddr,word(initial));count+=1
  # Other classes and missing scripts must not preview an effect operation.
  for k in (0,1,2,3,4,7,8,11,12):
   c.write(a4+kind+slot*2,word(k));c.write(sizeaddr,word(1024))
   c.write(script,word(0x406));c.write(a4+period+slot*2,word(1))
   before=c.read(DATA,data_size)
   run('timing_scene_effect_size',{13:slot,15:50,16:50})
   require(c.read(DATA,data_size)==before,('non-effect changed',k))
  c.write(a4+kind+slot*2,word(5));c.write(a4+table+26,long(0))
  before=c.read(DATA,data_size);run('timing_scene_effect_size',{13:slot,15:50,16:50})
  require(c.read(DATA,data_size)==before,'null script changed')
  c.write(a4+table+26,long(script))
  # Actual staging must invoke the helper even on the first effect interval,
  # and restore size together with every other native field afterwards.
  c.write(a4+kind+slot*2,word(5));c.write(script,word(0x406));c.write(sizeaddr,word(1024))
  c.write(a4+period+slot*2,word(1));c.write(a4+cursor+slot*2,word(0))
  put('intro_active',1);put('ocs_clock_active' if ocs else 'timing_active',0)
  put('ocs_clock_hz' if ocs else 'timing_hz',50,4)
  clock='ocs_clock_state' if ocs else 'timing_clock';put(clock,100,4)
  c.write(SLAVE+sy[clock]+4,long(10));c.write(a4+(-2048 if ocs else -252),long(100))
  put('ocs_pending' if ocs else 'release_pending',0)
  if ocs:put('ocs_prediction_cost',0,4)
  put('timing_scene_valid',0);run('timing_scene_snapshot')
  before=c.read(DATA,data_size);run('timing_scene_begin')
  require(c.get(sizeaddr)==1062,('first interval did not sample growth',c.get(sizeaddr)))
  run('timing_scene_end');require(c.read(DATA,data_size)==before,'staged effect leaked')
  return dict(model=model,cases=count,first_interval_and_restoration=True)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,models=rows),indent=2)+'\n');print(rows)
if __name__=='__main__':main()
