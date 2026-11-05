#!/usr/bin/env python3
"""E1 arithmetic differential against pinned native 68000 instructions."""
import argparse,json,random,struct
from pathlib import Path
from ocs_clock_check import machine
from ocs_display_check import Native,CODE,DATA,long,word
from ocs_reconstruct import ROOT,new_output,require

def check(build,model):
 c,sy=machine(build,model);ref=Native(ROOT/'tmp/game/WingCommander/data/Wing.english',model=model)
 rng=random.Random(13051);values=[0,1,255,256,257,32767,32768,65535,65536,0x7fffffff,0x80000000,0xffffffff,0xffffff00]
 pairs=[(a,b) for a in values for b in values]+[(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(1000)]
 pairs += [(rng.getrandbits(32),rng.randrange(-65535,65536)&0xffffffff) for _ in range(1000)]
 try:
  # The early radius rejection relies on a positive correction no larger
  # than the native equality coefficient, not an assumed Euclidean norm.
  table=struct.unpack('>256H',ref.read(CODE+0x2b718,512))
  require(min(table)==0 and max(table)<=27146,'native norm bound')
  for a,b in pairs:
   args=struct.pack('>II',a,b);regs={i:0x12340000+i for i in (*range(1,8),*range(9,17))}
   ref.run(0x2adb6,args,regs);c.run(0x2adb6,args,regs)
   require(c.reg(9)==ref.reg(9),('multiply',hex(a),hex(b),hex(c.reg(9)),hex(ref.reg(9))))
   require(all(c.reg(i)==ref.reg(i) for i in (*range(1,8),*range(10,17))),'multiply preserved registers')
   ref.run(0x2b6bc,registers={9:a,10:b});c.run(0x2b6bc,registers={9:a,10:b})
   require(all(c.reg(i)==ref.reg(i) for i in range(9,17)),('distance',hex(a),hex(b)))
  radius_cases=[]
  for scale in (0,1,255,256,65535,65536,0x3fffffff,0x40000000,0x7fffffff,0x80000000,0xffffffff):
   for r in (0,1,2,255,256,65535,0x3fffff,0x7fffffff,0xffffffff):
    for xyz in ((scale,0,0),(0,scale,0),(0,0,scale),(scale,scale,scale),(scale,(-scale)&0xffffffff,256)):
     radius_cases.append((xyz,r))
  radius_cases += [(tuple(rng.getrandbits(32) for _ in range(3)),rng.getrandbits(32)) for _ in range(1000)]
  radius_cases += [(tuple(rng.randrange(-1000000,1000000)&0xffffffff for _ in range(3)),rng.randrange(1,8000)) for _ in range(1000)]
  for xyz,r in radius_cases:
   for cpu in (c,ref):
    cpu.write(0x180000,b''.join(long(v) for v in xyz));cpu.run(0x2b950,long(0x180000)+long(r))
   require(c.reg(9)==ref.reg(9),('radius',xyz,r,c.reg(9),ref.reg(9)))
   require(all(c.reg(i)==ref.reg(i) for i in (2,3,4,5,6,7,*range(10,17))),'radius preserved registers')
  collisions=0
  for sample in range(100):
   state=bytearray(ref.read(DATA,0xf5b8))
   for slot in range(61):
    state[0x8e8c+2*slot:0x8e8e+2*slot]=word(rng.choice((0,8,9,10,11,12,13)))
    state[0x9288+2*slot:0x928a+2*slot]=word(rng.randrange(0,3000))
    xyz=[rng.randrange(-500000,500000) for _ in range(3)] if sample%2 else [rng.randrange(-1000,1000) for _ in range(3)]
    state[0x8928+12*slot:0x8934+12*slot]=struct.pack('>iii',*xyz)
   slot=sample%61;state[0x8e8c+slot*2:0x8e8e+slot*2]=word(8+sample%6)
   for cpu in (c,ref):cpu.write(DATA,bytes(state));cpu.run(0x156e6,word(slot))
   require(c.read(DATA,0xf5b8)==ref.read(DATA,0xf5b8),'collision scratch state')
   require(all(c.reg(i)==ref.reg(i) for i in range(1,17)),('collision registers',sample,[(i,c.reg(i),ref.reg(i)) for i in range(1,17) if c.reg(i)!=ref.reg(i)]))
   collisions+=1
  return dict(collision_scans=collisions,radius_cases=len(radius_cases),model=model,multiply_cases=len(pairs),distance_cases=len(pairs))
 finally:c.close();ref.close()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True);a=p.parse_args()
 result=dict(passed=True,checks=[check(a.build,m) for m in (1,2)])
 out=new_output(a.output);out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':main()
