import sys,json,struct,os
from harness_a import *
s=Session(sys.argv[1]);points=[]
try:
 route(s);s.input('JOY2_UP',1)
 target=rd(s,0x87480);data=read_bytes(s,target,1024);off=data.find(b'RRCSTEP1');assert off>=0;base=target+off
 for i in range(150):
  s.cmd('monitor fields 19')
  points.append(dict(field=field(s),sim=rd(s,0xa5d50),finish=rd(s,0xa5980,2),counter=rd(s,0xa5982,2),exit=rd(s,0xa59d0,2),hook=hex(rd(s,0xa5916))))
  if rd(s,0xa5916)!=0x87040:break
 else:raise RuntimeError('finish did not exit')
 s.input('JOY2_UP',0)
 cursor,steps,captured,quantum=struct.unpack('>4I',read_bytes(s,base+8,16))
 (s.out/'snapshot.bin').write_bytes(read_bytes(s,base+24,0x2e40))
 header=read_bytes(s,base+24+0x2e40,12);assert header[:8]==b'RRCHASH2';slots=struct.unpack_from('>I',header,8)[0];assert steps<slots
 (s.out/'hashes.bin').write_bytes(read_bytes(s,base+24+0x2e40+16,steps*4))
 result=dict(cursor=cursor,steps=steps,captured=captured,quantum=quantum,finish_time=rd(s,0xa5dc2),end_time=rd(s,0xa5d54),counter=rd(s,0xa5982,2),points=points,provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'finish.json').write_text(json.dumps(result,indent=2));s.shot('after-finish.png');print({k:v for k,v in result.items() if k not in ['points','provenance']},flush=True)
finally:s.quit()
