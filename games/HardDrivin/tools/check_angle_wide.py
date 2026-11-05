import json,os,shutil,struct
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-angle-wide';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-angle-wide.slave',out/'slave.slave');shutil.copyfile(ROOT/'tmp/angle-wide-inputs.json',out/'inputs.json');s=Session(out,'a500',out/'slave.slave',0x8520)
def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
def normalize(v):
 v-=trunc(v,1440)*1440
 if v>720:v-=1440
 if v< -720:v+=1440
 return v
try:
 s.boot();got={};inputs=json.loads((out/'inputs.json').read_text())
 for bank,b in s.dump_banks('angles'):
  for name,sig,unit in [('normalize',b'HDANORM1',4),('contact',b'HDACONT1',8),('motion',b'HDAMOTN1',8)]:
   i=b.find(sig)
   if i>=0:assert name not in got;got[name]=b[i+8:i+8+len(inputs[name])*unit]
 assert [x[0] for x in struct.iter_unpack('>i',got['normalize'])]==[normalize(v) for v in inputs['normalize']]
 for kind in ['contact','motion']:
  expected=[]
  for rate,n,current,last,carry in inputs[kind]:
   if current-last not in [0,-1440,1440]:carry=0
   full=(rate*n//8 if kind=='contact' else rate*n*8192)+carry;q=trunc(full,65536);remainder=full-q*65536
   angle=current+q
   if n>8:angle=normalize(angle)
   expected.append((angle,angle,remainder))
  actual=list(struct.iter_unpack('>hhi',got[kind]));assert actual==expected,(kind,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y][:10])
 result=dict(passed=True,normalize_cases=len(inputs['normalize']),contact_cases=len(inputs['contact']),motion_cases=len(inputs['motion']));(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
