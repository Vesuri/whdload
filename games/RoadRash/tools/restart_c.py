import sys,json,struct,os
from harness_a import *
s=Session(sys.argv[1]);points=[]
def state(label):
 target=rd(s,0x87480);data=read_bytes(s,target,1024);off=data.find(b'RRCSTEP1');assert off>=0
 cursor,steps,captured,quantum=struct.unpack_from('>4I',data,off+8)
 v=dict(label=label,field=field(s),cursor=cursor,steps=steps,captured=captured,quantum=quantum,hook=rd(s,0xa5916),steering=rd(s,0xa7262,2),raw=read_bytes(s,0xa598c,1).hex());points.append(v);print(v,flush=True);return v
try:
 route(s);s.input('JOY2_UP',1);advance(s,1600);s.input('JOY2_UP',0)
 a=state('first race');assert a['captured']==1457
 s.cmd('monitor key 59 1');s.cmd('monitor fields 39');s.cmd('monitor key 59 0')
 for i in range(20):
  s.cmd('monitor fields 19')
  if rd(s,0xa5916)!=0x87040:break
 else:raise RuntimeError('F10 did not exit race')
 s.shot('after-exit.png')
 route(s);b=state('second race');assert b['field']==100 and b['captured']==0 and b['cursor']<=100 and b['steps']<=100
 s.input('JOY2_RIGHT',1);advance(s,120);c=state('new steering');assert c['steering']!=0
 s.input('JOY2_RIGHT',0);advance(s,200);d=state('released');assert d['steering']==0
 s.shot('second-race.png')
 (s.out/'restart.json').write_text(json.dumps(dict(points=points,provenance=provenance(os.environ['SLAVE'],s)),indent=2))
finally:s.quit()
