import json,os,struct,shutil
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-presentation-math';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-presentation-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();hits=[]
 for bank,b in s.dump_banks('presentation-math'):
  i=b.find(b'HDPRMAT1')
  if i>=0:hits.append(b[i+8:i+8+12600])
 assert len(hits)==1;raw=hits[0];cases=0
 for n in range(9):
  expected=[1];age=0
  for k in range(74):
   height=max(0,256-4*age);age=min(72,age+n);expired=int(age==72)
   expected += [0,height,age//8,expired,age,1-expired];cases+=1
   if expired:
    expected += [0,0,72,0];break
  actual=struct.unpack_from('>'+str(len(expected))+'H',raw,n*900)
  assert tuple(expected)==actual,(n,expected,actual)
  expected=[];remain=480
  for k in range(125):
   remain=max(0,remain-n);expected += [(remain+7)//8,remain]
  assert struct.unpack_from('>250H',raw,8100+n*500)==tuple(expected),n
 r=dict(passed=True,recovery_transitions=cases,overlay_transitions=1125,zero_time=True,one_time_initialization=True,one_shot_expiry=True,ground_hold=True);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
finally:s.close()
