import json,os,shutil,struct,sys
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof'/(sys.argv[1] if len(sys.argv)>1 else 's4-ghost-post-math');out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-ghost-post-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520);s.env['WHD_ARGS']+=' CUSTOM1=1'
try:
 s.boot();hits=[]
 for _,b in s.dump_banks('post-math'):
  i=b.find(b'HDGHPMA1')
  if i>=0:hits.append(b[i+8:i+8+2448])
 assert len(hits)==1;raw=hits[0];offset=0
 for delta in [-32768,-32767,-1234,-1,0,1,1234,32766,32767]:
  for fields in [1,2,3,7,8,9,1392,65535]:
   actual=struct.unpack_from('>H',raw,offset)[0];expected=((abs(delta)*48//fields)*(-1 if delta<0 else 1))&65535;assert actual==expected,(delta,fields,actual,expected);offset+=2
 for phase in range(48):
  for age in [0,1,7,8,47,48,1391,1392]:
   actual=struct.unpack_from('>IH',raw,offset);expected=(0x10000+(age+phase)//48*12,(age+phase)%48);assert actual==expected,(phase,age,actual,expected);offset+=6
 assert offset==len(raw);result=dict(passed=True,derivative_cases=72,cursor_cases=384);(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
