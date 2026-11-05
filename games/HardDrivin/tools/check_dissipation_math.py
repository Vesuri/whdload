import json,os,shutil,struct,sys
from capture_demo import ROOT
from capture_session import Session
from dissipation_model import update
os.chdir(ROOT);out=ROOT/'tmp/prof'/sys.argv[1];out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-dissipation-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520);s.env['WHD_ARGS']+=' CUSTOM1=1';cases=json.loads((ROOT/'tmp/dissipation-inputs.json').read_text())
try:
 s.boot();hits=[]
 for _,b in s.dump_banks('dissipation'):
  i=b.find(b'HDDISSM1')
  if i>=0:hits.append(b[i+8:i+8+len(cases)*10])
 assert len(hits)==1
 limited=0
 for i,c in enumerate(cases):
  e=update(*c);got=struct.unpack_from('>ihhh',hits[0],i*10);expected=(e['delta'],e['value'],e['carry'],e['value']);assert got==expected,(i,c,got,expected);limited+=e['limited']
 result=dict(passed=True,cases=len(cases),limited=limited);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
