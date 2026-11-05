import os,sys,json,struct
from harness_a import *
if not any(x.upper().startswith('CUSTOM2=') for x in os.environ.get('WHD_ARGS','').split()):
 os.environ['WHD_ARGS']=os.environ.get('WHD_ARGS','')+' CUSTOM2=1'
s=Session(sys.argv[1]);hashes=[];points=[];driven=[];held={};coverage=[];fraction_addr=None;previous_lateral=None
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
 for t in range(100,9761,interval):
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
   wanted={'JOY2_UP':int(riding and speed<int(os.environ.get('RR_DRIVER_SPEED','65535'))),'JOY2_LEFT':int(riding and estimate>lane+deadzone),'JOY2_RIGHT':int(riding and estimate<lane-deadzone),'JOY2_FIRE_BUTTON':int(riding and t%300<60 and os.environ.get('RR_DRIVER_ATTACKS','1')=='1')}
   events=[(k,v) for k,v in wanted.items() if held.get(k,0)!=v]
   for k,v in events:held[k]=v;driven.append([t,k,v])
  for key,value in events:s.input(key,value)
  if t%500==0:
   point=dict(field=t,published=len(hashes),position=rd(s,0xa5d64),camera=rd(s,0xa5d1e),finish=rd(s,0xa5980,2),exit=rd(s,0xa59d0,2),crash=read_bytes(s,0xa5dce,1).hex(),damage=rd(s,0xa59da,2))
   points.append(point);print(point,flush=True)
 else:collect()
 addr=0xa6426
 if hasattr(s,'public_main_base'):addr+=s.public_main_base-0x80000
 s.cmd(f'watch *(short*){addr:#x}')
 for i in range(7):
  print(s.cmd('continue',timeout=60),flush=True)
  s.cmd('maintenance flush register-cache')
  print(s.cmd('info registers'),flush=True)
  print('field',field(s),'table',read_bytes(s,0x8d128,64).hex(),flush=True)
finally:s.quit()
