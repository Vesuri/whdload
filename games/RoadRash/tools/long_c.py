import os,sys,json,struct
from harness_a import *
os.environ['WHD_ARGS']=os.environ.get('WHD_ARGS','')+' CUSTOM2=1'
s=Session(sys.argv[1]);hashes=[];points=[];driven=[];held={}
try:
 route(s)
 target=rd(s,0x87480);data=read_bytes(s,target,1024);off=data.find(b'RRCSTEP1');assert off>=0
 base=target+off;ha=base+24+0x2e40
 def collect():
  h=read_bytes(s,ha,16);assert h[:8]==b'RRCHASH3'
  slots,published=struct.unpack_from('>II',h,8)
  assert len(hashes)<=published and published-len(hashes)<=slots,('lost hashes',len(hashes),published,slots)
  ring=struct.unpack('>'+str(slots)+'I',read_bytes(s,ha+16,slots*4))
  for tick in range(len(hashes)+1,published+1):hashes.append(ring[tick&(slots-1)])
 tape=json.loads(Path(os.environ['RR_TAPE_PATH']).read_text())
 schedule={}
 for t,key,value in tape['events']:schedule.setdefault(t,[]).append((key,value))
 if os.environ.get('RR_ADAPT'):
  schedule={t:[] for t in range(100,tape['end_field']+1,20)}
 for t in range(500,tape['end_field']+1,500):schedule.setdefault(t,[])
 collect()
 for t,events in sorted(schedule.items()):
  advance(s,t);collect()
  if os.environ.get('RR_ADAPT'):
   crash=struct.unpack('>b',read_bytes(s,0xa5dce,1))[0]
   lateral=struct.unpack('>h',read_bytes(s,0xa5d90,2))[0]
   riding=crash<0 and t<tape['end_field']
   wanted={'JOY2_UP':int(riding),'JOY2_LEFT':int(riding and lateral>64),'JOY2_RIGHT':int(riding and lateral< -64),'JOY2_FIRE_BUTTON':int(riding and t%300<60)}
   events=[(k,v) for k,v in wanted.items() if held.get(k,0)!=v]
   for k,v in events:held[k]=v;driven.append([t,k,v])
  for key,value in events:s.input(key,value)
  if t%500==0:
   special=rd(s,0x941e2);assert 0xa5d60<=special<0xa6ee0
   point=dict(field=t,published=len(hashes),position=rd(s,0xa5d64),camera=rd(s,0xa5d1e),special=hex(special),special_position=rd(s,special+4),special_flags=read_bytes(s,special+0x68,2).hex(),cop_position=rd(s,0xa5de4),cop_disabled=rd(s,0xa59e6,2),crash=read_bytes(s,0xa5dce,1).hex())
   points.append(point);print(point,flush=True)
 capture=struct.unpack('>4I',read_bytes(s,base+8,16));assert capture[2]==int(os.environ.get('RR_CAPTURE','5501')),capture
 (s.out/'snapshot.bin').write_bytes(read_bytes(s,base+24,0x2e40))
 target=rd(s,0x8f06c);data=read_bytes(s,target,1024);off=data.find(b'RRCSEV01');assert off>=0
 count,overflow,capacity,size=struct.unpack_from('>4I',data,off+8);assert count<=capacity and overflow==0 and size==8
 events=[dict(field=f,kind=k,value=v) for f,k,v in struct.iter_unpack('>IHH',read_bytes(s,target+off+24,count*size))]
 (s.out/'hashes.bin').write_bytes(struct.pack('>'+str(len(hashes))+'I',*hashes))
 if os.environ.get('RR_ADAPT'):
  (s.out/'driven-tape.json').write_text(json.dumps(dict(version=1,start_field=100,end_field=tape['end_field'],events=driven),indent=2)+'\n')
 result=dict(published=len(hashes),capture=capture,points=points,events=events,stats=counters(s,stats_address(s)),provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'long.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('final.png');print('published',len(hashes),'sound events',len(events),flush=True)
finally:s.quit()
