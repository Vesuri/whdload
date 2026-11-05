import sys,json,struct
from harness_a import *
s=Session(sys.argv[1])
try:
 initial=route(s);main=rd(s,0x87480);head=read_bytes(s,main,4);assert head[:2]==bytes.fromhex('6100'),head.hex()
 target=main+2+struct.unpack_from('>h',head,2)[0];code=read_bytes(s,target,256);off=code.find(b'RRACTOR1');assert off>=0
 actor_stats=target+off;data=read_bytes(s,main,1024);off=data.find(b'RRCSTEP1');assert off>=0;step_stats=main+off
 def point():
  state,base,count,allocation=struct.unpack('>4I',read_bytes(s,actor_stats+8,16));cursor,steps,_,quantum=struct.unpack('>4I',read_bytes(s,step_stats+8,16))
  if field(s)>100:assert state==3,(state,base,count)
  actual=base if state==3 else 0xa5d60
  if state==3:
   assert count==167 and allocation>=0x200000
   guard=bytes.fromhex('a55aa55a')*4
   assert read_bytes(s,allocation-16,16)==guard and read_bytes(s,allocation+0x1180,16)==guard
  return dict(field=field(s),cursor=cursor,steps=steps,quantum=quantum,frames=counters(s,stats_address(s))['frames'],position=rd(s,actual+4),state=state,base=hex(actual),allocation=hex(allocation))
 begin=int(os.environ.get('RR_BEGIN','100'))
 if begin>100:advance(s,begin)
 points=[point()];s.input('JOY2_UP',1)
 for f in [begin+200,begin+500,begin+900]:advance(s,f);points.append(point());print(points[-1],flush=True)
 (s.out/'actors.bin').write_bytes(read_bytes(s,int(points[-1]['base'],16),0x1180))
 result=dict(points=points,provenance=provenance(os.environ['SLAVE'],s));(s.out/'cost.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('final.png')
finally:s.quit()
