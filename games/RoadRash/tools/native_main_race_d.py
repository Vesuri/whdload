import sys,os,json,struct
from harness_a import *
s=Session(sys.argv[1]);points=[];held={};tape=[]
try:
 route(s)
 for t in range(100,40001,20):
  if t>100:s.cmd('monitor fields 19')
  if rd(s,0xa5916)!=0x87040:break
  assert field(s)==t
  if t%100==0:points.append(snapshot(s))
  crash=struct.unpack('>b',read_bytes(s,0xa5dce,1))[0];lateral=struct.unpack('>h',read_bytes(s,0xa5d90,2))[0];riding=crash<0 and not rd(s,0xa5980,2)
  wanted={'JOY2_UP':int(riding),'JOY2_LEFT':int(riding and lateral>64),'JOY2_RIGHT':int(riding and lateral<-64),'JOY2_FIRE_BUTTON':int(riding and t%300<60)}
  for k,v in wanted.items():
   if held.get(k,0)!=v:s.input(k,v);held[k]=v;tape.append([t,k,v])
  if t%1000==0:print(t,hex(rd(s,0xa5d64)),rd(s,0xa5980,2),flush=True)
 else:raise RuntimeError('native race did not end')
 result=dict(points=points,tape=tape,end=field(s),finish=rd(s,0xa5980,2),finish_time=rd(s,0xa5dc2),end_time=rd(s,0xa5d54));s.shot('end.png')
 for k in held:s.input(k,0)
 result['restart']=route(s);assert rd(s,0xa5980,2)==0;s.shot('restart.png')
 (s.out/'race.json').write_text(json.dumps(result,indent=2)+'\n');print('ended',result['end'],'finish',result['finish'],'points',len(points),flush=True)
finally:s.quit()
