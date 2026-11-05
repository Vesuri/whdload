import os,sys,json,struct
from harness_a import *
if not any(x.upper().startswith('CUSTOM2=') for x in os.environ.get('WHD_ARGS','').split()):
 os.environ['WHD_ARGS']=os.environ.get('WHD_ARGS','')+' CUSTOM2=1'
s=Session(sys.argv[1]);hashes=[];points=[];driven=[];held={};coverage=[];fraction_addr=None;previous_lateral=None;seek_crash=False
try:
 route(s)
 target=rd(s,0x87480);data=read_bytes(s,target,1024);off=data.find(b'RRCSTEP1');assert off>=0
 base=target+off;ha=base+24+0x2e40
 if os.environ.get('RR_STEERING_COVERAGE'):
  hook=rd(s,0x8b97c);code=read_bytes(s,hook,128);idx=code.find(bytes.fromhex('41fa'));assert idx>=0
  fraction_addr=hook+idx+2+struct.unpack_from('>h',code,idx+2)[0]
 finish_line=rd(s,0x947fc,2);print('finish line',finish_line,flush=True)
 def collect():
  h=read_bytes(s,ha,16);assert h[:8]==b'RRCHASH3'
  slots,published=struct.unpack_from('>II',h,8)
  assert len(hashes)<=published and published-len(hashes)<=slots,('lost hashes',len(hashes),published,slots)
  ring=struct.unpack('>'+str(slots)+'I',read_bytes(s,ha+16,slots*4))
  for tick in range(len(hashes)+1,published+1):hashes.append(ring[tick&(slots-1)])
 tape=None
 if os.environ.get('RR_TAPE_PATH'):
  tape=json.loads(Path(os.environ['RR_TAPE_PATH']).read_text());schedule={}
  for t,k,v in tape['events']:schedule.setdefault(t,[]).append((k,v))
 interval=int(tape.get('driver_interval',20) if tape else os.environ.get('RR_DRIVER_INTERVAL','20'));assert interval>=2 and 500%interval==0
 collect()
 for t in range(100,30001,interval):
  if t>100:s.cmd(f'monitor fields {interval-1}')
  current=field(s)
  if t%500==0 or rd(s,0xa5916)!=0x87040:collect()
  if rd(s,0xa5916)!=0x87040:break
  assert current==t,(current,t)
  if fraction_addr is not None:
   flags=read_bytes(s,0xa5dc8,1)[0];crash=struct.unpack('>b',read_bytes(s,0xa5dce,1))[0];fraction=struct.unpack('>i',read_bytes(s,fraction_addr,4))[0]
   assert -int(os.environ.get('RR_FRACTION_BOUND','4096'))<fraction<int(os.environ.get('RR_FRACTION_BOUND','4096')),fraction
   coverage.append(dict(field=t,skid=bool(flags&32),airborne=bool(flags&1),crash=crash,fraction=fraction))
  if tape:events=schedule.get(t,[])
  else:
   crash=struct.unpack('>b',read_bytes(s,0xa5dce,1))[0]
   lateral=struct.unpack('>h',read_bytes(s,0xa5d90,2))[0]
   riding=crash<0 and not rd(s,0xa5980,2)
   speed=rd(s,0xa5d72,2)
   estimate=lateral+(lateral-previous_lateral)*int(os.environ.get('RR_DRIVER_PREDICT','0')) if previous_lateral is not None else lateral
   previous_lateral=lateral
   lane=int(os.environ.get('RR_DRIVER_LANE','0'));deadzone=int(os.environ.get('RR_DRIVER_DEADZONE','64'))
   if not riding:seek_crash=False
   elif speed>=int(os.environ.get('RR_CRASH_SPEED','10000')):seek_crash=True
   if seek_crash:lane=int(os.environ.get('RR_CRASH_LANE','-384'))
   wanted={'JOY2_UP':int(riding and speed<int(os.environ.get('RR_DRIVER_SPEED','65535'))),'JOY2_LEFT':int(riding and estimate>lane+deadzone),'JOY2_RIGHT':int(riding and estimate<lane-deadzone),'JOY2_FIRE_BUTTON':int(riding and t%300<60 and os.environ.get('RR_DRIVER_ATTACKS','1')=='1')}
   events=[(k,v) for k,v in wanted.items() if held.get(k,0)!=v]
   for k,v in events:held[k]=v;driven.append([t,k,v])
  for key,value in events:s.input(key,value)
  if t%500==0:
   point=dict(field=t,published=len(hashes),position=rd(s,0xa5d64),camera=rd(s,0xa5d1e),finish=rd(s,0xa5980,2),exit=rd(s,0xa59d0,2),crash=read_bytes(s,0xa5dce,1).hex(),damage=rd(s,0xa59da,2))
   points.append(point);print(point,flush=True)
 else:raise RuntimeError('race did not end')
 capture=struct.unpack('>4I',read_bytes(s,base+8,16));assert capture[0]==capture[2] and capture[1]==len(hashes),capture
 (s.out/'snapshot.bin').write_bytes(read_bytes(s,base+24,0x2e40))
 target=rd(s,0x8f06c);data=read_bytes(s,target,1024);off=data.find(b'RRCSEV01');assert off>=0
 count,overflow,capacity,size=struct.unpack_from('>4I',data,off+8);assert count<=capacity and overflow==0 and size==8
 events=[dict(field=f,kind=k,value=v) for f,k,v in struct.iter_unpack('>IHH',read_bytes(s,target+off+24,count*size))]
 (s.out/'hashes.bin').write_bytes(struct.pack('>'+str(len(hashes))+'I',*hashes))
 if not tape:(s.out/'driven-tape.json').write_text(json.dumps(dict(version=1,driver_interval=interval,start_field=100,end_field=t,events=driven),indent=2)+'\n')
 result=dict(steering_coverage=coverage,finish_line=finish_line,finish=rd(s,0xa5980,2),finish_time=rd(s,0xa5dc2),end_time=rd(s,0xa5d54),published=len(hashes),capture=capture,points=points,events=events,stats=counters(s,stats_address(s)),provenance=provenance(os.environ['SLAVE'],s))
 (s.out/'race.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('final.png');print('published',len(hashes),'finish',result['finish'],'sound events',len(events),flush=True)
 if os.environ.get('RR_RESTART'):
  for key in ['JOY2_UP','JOY2_LEFT','JOY2_RIGHT','JOY2_FIRE_BUTTON']:s.input(key,0)
  normal=route(s);fresh=struct.unpack('>4I',read_bytes(s,base+8,16));assert fresh[0]<=100 and fresh[1]<=100 and fresh[2]==0 and rd(s,0xa5980,2)==0
  result['next_race']=dict(state=normal,capture=fresh)
  if os.environ.get('RR_ROAD_LISTING'):
   import re
   listing=Path(os.environ['RR_ROAD_LISTING']).read_text(encoding='latin1')
   def symbol(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
   slave_base=rd(s,0x8bdf2)-symbol('step_actor_road_copy')
   road=read_bytes(s,slave_base+symbol('step_road_fraction'),12)
   actors=read_bytes(s,slave_base+symbol('step_actor_road_fraction'),140)
   assert road==bytes(12) and actors==bytes(140),(road.hex(),actors.hex())
   result['next_race']['road_state']=dict(player=road.hex(),actors=actors.hex())
  (s.out/'race.json').write_text(json.dumps(result,indent=2)+'\n');s.shot('next-race.png');print('next race',fresh,flush=True)
finally:s.quit()
