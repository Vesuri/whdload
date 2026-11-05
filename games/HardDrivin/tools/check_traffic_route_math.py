import json,os,shutil,struct,sys
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof'/(sys.argv[1] if len(sys.argv)>1 else 's4-traffic-route-math');out.mkdir(exist_ok=False)
shutil.copyfile(ROOT/'tmp/build/s4-traffic-turn-route.slave',out/'slave.slave');shutil.copyfile(ROOT/'tmp/traffic-route-inputs.json',out/'inputs.json')
s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();cases=json.loads((out/'inputs.json').read_text());hits=[]
 for bank,b in s.dump_banks('route'):
  i=b.find(b'HDTRROU1')
  if i>=0:hits.append(b[i+8:i+8+len(cases)*92])
 assert len(hits)==1;hidden_crossings=0
 for i,c in enumerate(cases):
  got,ref=hits[0][i*92:i*92+46],hits[0][i*92+46:(i+1)*92]
  assert got==ref,(i,c,got.hex(),ref.hex())
  assert struct.unpack_from('>H',got,16)[0]==(c[5]+c[7])%200
  if i>=120 and c[5]==0:hidden_crossings+=struct.unpack_from('>II',got)!=(c[0],c[1]) or got[13]!=c[2]
 if len(cases)>=126:assert hidden_crossings>0
 result=dict(passed=True,prepared_zero_net_cases=max(0,len(cases)-120),prepared_zero_net_route_changes=hidden_crossings,cases=len(cases),reference='native CF02..CFE4 and D380..D406 instruction copies',max_crossings=max(abs(c[5]//200) for c in cases));(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
