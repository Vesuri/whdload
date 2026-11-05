#!/usr/bin/env python3
"""Native depth-sort ties: attached death explosions stay over their ship."""
import argparse,json,struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE,DATA,word
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output,require
from variants import get


def check(build,variant,model,capture):
 c,sy=machine(build,variant,model);v=get(variant);ocs=variant=='ocs';a4=DATA+v.A4_BASE
 offsets=(0xe8e,0xf86,0x3058,0x252e,0x20f8,0x227c,-4326) if ocs else (0x1700,0x17f8,0x3a6a,0x24de,0x245e,0x2cee,-4456)
 kind,models,owner,depth,screen,size,draw=[a4+x for x in offsets]
 sort=0x2ba2c if ocs else 0x2c9b6
 def run():c.run(SLAVE-CODE+sy['effect_order'])
 def order():
  raw=struct.unpack('>65h',c.read(draw,130));return list(raw[:raw.index(-1)])
 def setup(parent=1,explosion=17,dist=1000,mdl=49,pkind=12,who=None):
  c.write(kind,bytes(130));c.write(SLAVE+sy['intro_active'],word(1))
  for slot,k,d in ((parent,pkind,1000),(explosion,5,dist),(22,5,1000),(34,4,1500),(40,4,900)):
   c.write(kind+slot*2,word(k));c.write(depth+slot*2,word(d));c.write(screen+slot*2,word(0));c.write(size+slot*2,word(10));c.write(models+slot*2,word(0))
  c.write(models+explosion*2,word(mdl));c.write(owner+explosion,bytes([parent if who is None else who]))
 def verify(before,want):
  regs={r:0x12340000+r for r in (1,2,3,4,9,10,11,12)}
  c.run(SLAVE-CODE+sy['effect_order'],registers=regs)
  require(order()==want,('order',order(),want))
  after=c.read(DATA,v.HUNKS[1][2]);off=draw-DATA
  require(before[:off]==after[:off] and before[off+130:]==after[off+130:],'changed game state outside draw list')
  require(all(c.reg(r)==x for r,x in regs.items()),'register clobber')
 cases=0;native_reversals=0;live_reversals=0
 try:
  for parent,explosion in ((1,17),(8,10),(9,60)):
   for dist in (999,1000,1001):
    setup(parent,explosion,dist);c.run(sort);original=order();want=original[:]
    if dist==1000 and want.index(parent*2)>want.index(explosion*2):
     want.remove(parent*2);want.insert(want.index(explosion*2),parent*2);native_reversals+=1
    verify(c.read(DATA,v.HUNKS[1][2]),want);cases+=1
    # Both possible tie orders, with another tied object between the pair.
    if dist==1000:
     for seq in ((68,explosion*2,44,parent*2,80),(68,parent*2,44,explosion*2,80)):
      c.write(draw,struct.pack('>6h',*seq,-1));want=list(seq)
      if want.index(parent*2)>want.index(explosion*2):want.remove(parent*2);want.insert(want.index(explosion*2),parent*2)
      verify(c.read(DATA,v.HUNKS[1][2]),want);cases+=1
  for kw in ({'mdl':51},{'pkind':0},{'who':255},{'who':10}):
   setup(**kw);c.run(sort);verify(c.read(DATA,v.HUNKS[1][2]),order());cases+=1
  setup();c.run(sort);c.write(SLAVE+sy['intro_active'],word(0));verify(c.read(DATA,v.HUNKS[1][2]),order());cases+=1
  if capture and not ocs:
   for path in sorted(capture.glob('*-shown.bin')):
    c.write(DATA,path.read_bytes());c.write(SLAVE+sy['intro_active'],word(1));c.run(sort)
    old=order();before=c.read(DATA,v.HUNKS[1][2]);run();new=order()
    require(sorted(new)==sorted(old),'lost object')
    if c.get(kind+34)==5 and c.get(models+34)==49 and 2 in old and 34 in old:
     if c.get(depth+2)==c.get(depth+34):
      require(new.index(2)<new.index(34),'captured ship drawn over its explosion')
      live_reversals+=old.index(2)>old.index(34)
    off=draw-DATA;after=c.read(DATA,v.HUNKS[1][2]);require(before[:off]==after[:off] and before[off+130:]==after[off+130:],'capture state leak')
   require(live_reversals>0,'capture failed to reproduce reported order reversal')
  require(native_reversals>0,'native negative control missed tie')
  return dict(model=model,cases=cases,native_reversals=native_reversals,captured_reversals=live_reversals)
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('--capture',type=Path);p.add_argument('--output',required=True)
 a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 rows=[check(a.build,a.variant,m,a.capture) for m in ((1,2) if a.variant=='ocs' else (2,4))]
 (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,models=rows),indent=2)+'\n');print(rows)
if __name__=='__main__':main()
