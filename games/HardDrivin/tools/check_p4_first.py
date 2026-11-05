"""Assembled 68000 old/new comparisons for the first P4 arithmetic changes."""
from pathlib import Path
import json,random,re,struct,subprocess,os
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
roots=[Path('tmp/p4-before'),Path('src')];symbols=[]
def part(s,a,b):return s[s.index(a):s.index(b,s.index(a))]+'\n'
for index,root in enumerate(roots):
 time=(root/'HardDrivinTime.s').read_text();phase=(root/'HardDrivinPhase.s').read_text().split('_phase_power:')[0];proj=(root/'HardDrivinProjection.s').read_text();contact=(root/'HardDrivinContact.s').read_text();motion=(root/'HardDrivinMotion.s').read_text()
 txt='VERIFY_DRIVETRAIN_PHASE equ 1\nVERIFY_TIME_DISSIPATION equ 1\nTIME_FIELDS_PER_STEP equ 8\n'+part(phase,'PH_VALID equ',' dc.b')
 txt+='\nSS_VELOCITY_CARRY equ 0\nSS_VELOCITY_LAST equ 2\nSS_RPM_CARRY equ 10\nSS_RPM_LAST equ 12\nSS_RPM_GEAR equ 14\n'
 drivetrain=(root/'HardDrivinDrivetrain.s').read_text()
 txt+=part(drivetrain,'_drivetrain_power_state:','\n\tENDC')+'\n'
 scalar=(root/'HardDrivinScalar.s').read_text()
 txt+=part(scalar,'_time_velocity_add:','_time_throttle_up:')+part(scalar,'_time_rpm_delta:','_time_reset_scalars:')+Path('src/HardDrivinDissipation.s').read_text()
 txt+=part(time,'_time_scale_word:','; Q16 companion')+part(time,'_time_scale_q16:','; Exact signed-long times unsigned-word')+part(time,'_time_normalize_angle:','; Convert unsigned pending')
 txt+=part(phase,'_phase_prepare_anchor:','_phase_gear:')+part(phase,'_phase_add_position:','_phase_published:')+(phase[phase.index('_phase_scalar_step:'):]+'\n')
 txt+=part(proj,'_projection_quantized_components:','; D0.W velocity;')+part(proj,'_projection_components:','_projection_integrate:')
 txt+=part(proj,'_projection_integer_components:','; D0.W eighth-velocity')+part(phase,'_phase_published:','; A0: native-phase anchor')
 txt+='MS_FALL_CARRY equ 18\nMS_FALL_LAST equ 20\nMS_FALL_ACCEL equ 30\n_motion_state: dcb.b 32,0\n_motion_position_state: dcb.b 20,0\n'
 txt+=part(motion,'_motion_drift:','; Entry uses a jump patch')+part(motion,'_motion_fall_position:','; D0.W fall velocity')+part(contact,'_contact_project_q16:','; Full Q16 roll/pitch')+part(contact,'_contact_pitch_projection:','_contact_roll:')
 txt+=part(motion,'_motion_fall_displacement:','\tIFD VERIFY_FALL_WIDE_MATH')
 txt+=part(time,'_time_product_s32_u16:','; D0 signed-long angular')+part(contact,'_contact_scale_rate:','; Native roll cosine')
 txt+='\n_time_scalar_fields: dc.w 8\n_time_scalar_state: dcb.b 16,0\n_phase_state: dcb.b 78,0\n_phase_speed_cache: dcb.w 4,0\n_phase_power_status: dc.w 0\n_projection_state: dcb.b 36,0\n_drivetrain_state: dcb.b 16,0\n'
 addr=0x400100+index*0x10000;stem=Path(f'tmp/p4-first-{index}');stem.with_suffix('.s').write_text(f' org ${addr:x}\n'+txt)
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(stem.with_suffix('.lst')),'-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 symbols.append({n:int(v,16) for v,n in re.findall(r'^([0-9A-F]+) (_\w+)$',stem.with_suffix('.lst').read_text(),re.M)});write(addr,stem.with_suffix('.bin').read_bytes())
stop=0x490000;sp=0x4ffff0;rng=random.Random(404);counts={}
def run(index,name,ds=(),setup=None):
 sy=symbols[index];reg(17,0x2000)
 for k in range(1,17):reg(k,k*0x10101)
 reg(5,a4);reg(7,sy['_phase_state']);reg(8,sp);pack(sp,'I',stop)
 for j,v in enumerate(ds):reg(9+j,v&0xffffffff)
 if setup:setup(sy)
 saved=[reg(k) for k in range(1,17)]
 ok(u.uc_emu_start(h,sy[name],stop,1000000,5000));assert reg(18)==stop and reg(8)==sp+4
 return sy,saved,[reg(k) for k in range(1,17)]
try:
 for value in list(range(-3000,3001))+[-2147483648,2147483647]+[rng.randint(-2147483648,2147483647) for _ in range(10000)]:
  a=run(0,'_time_normalize_angle',[value]);b=run(1,'_time_normalize_angle',[value]);assert all(a[2][k]==b[2][k] for k in range(16) if k!=6),value
  m=abs(value)%1440*(-1 if value<0 else 1);m=m-1440 if m>720 else m+1440 if m< -720 else m
  assert b[2][8]==m&0xffffffff and all(b[2][k]==b[1][k] for k in range(16) if k not in [7,8])
 counts['angle']=16003
 for i in range(20000):
  rate=rng.choice([0,rng.randint(-32768,32767)]);n=rng.choice([0,1,7,8,9,32767,32768,65535,rng.randrange(65536)]);carry=rng.randint(-7,7)
  a=run(0,'_time_scale_word',[rate,n,carry]);b=run(1,'_time_scale_word',[rate,n,carry]);assert all(a[2][k]==b[2][k] for k in range(16) if k!=6),(rate,n,carry)
 counts['scale_word']=20000
 for i in range(10000):
  av=rng.randrange(32768*8)*8192;cur=av if i%2 else rng.randrange(32768*65536);end=rng.randrange(32768);remain=rng.randint(1,8);dt=rng.randint(1,remain)
  def setup(sy):pack(0x480000,'II',av,cur);reg(1,0x480000)
  outs=[]
  for j in [0,1]:
   z=run(j,'_phase_scalar_step',[end,dt,remain],setup);outs.append((z[2][8],read(0x480004,4)))
  assert outs[0]==outs[1],(av,cur,end,dt,remain)
 counts['phase_scalar']=10000
 for i in range(10000):
  v=rng.randrange(21842*64)*1024 if i%2 else rng.randrange(21842)*65536
  tr=rng.choice([[0,16384,0,16384],[16384,0,0,16384],[-16384,0,0,16384],[rng.randint(-16384,16384) for _ in range(4)]]);pack(a4-0x6bb8,'4h',*tr)
  def setup(sy):reg(1,0x480000);write(0x480000,b'X'*12)
  outs=[]
  for j in [0,1]:
   z=run(j,'_phase_project',[v],setup);assert z[1][:7]==z[2][:7] and z[1][8:]==z[2][8:];outs.append(read(0x480000,12))
  assert outs[0]==outs[1],(v,tr)
 counts['phase_project']=10000
 for i in range(5000):
  dt=rng.randint(1,8);vec=[rng.choice([0,rng.randint(-0x30000000,0x30000000)]) for _ in range(3)];carries=[rng.randint(-65535,65535) for _ in range(3)];pos=[rng.randint(-1000000,1000000) for _ in range(3)]
  def setup(sy):pack(sy['_phase_state']+10,'H',dt);pack(sy['_phase_state']+60,'3i',*vec);pack(sy['_projection_state']+24,'3i',*carries);pack(a4-0x6704,'3i',*pos)
  outs=[]
  for j in [0,1]:
   z=run(j,'_phase_add_position',setup=setup);outs.append((read(a4-0x6704,12),read(z[0]['_projection_state']+24,12)))
  assert outs[0]==outs[1],(dt,vec,carries,pos)
 counts['phase_position']=5000
 for i in range(5000):
  v=rng.randrange(2001*8)*8192;r=rng.randrange(6501*8)*8192;k=rng.randint(1,4);br=rng.choice([0,255])
  def setup(sy):
   pack(sy['_phase_power_status'],'h',1 if i%3 else 0);pack(sy['_phase_speed_cache'],'4h',(r>>16)+(i%3==2),k,model.engine_speed((r>>16)+(i%3==2),k),1 if i%3 else 0);write(sy['_time_scalar_state'],b'X'*16);pack(sy['_phase_state']+12,'I',v);pack(sy['_phase_state']+20,'I',r);pack(sy['_phase_state']+32,'H',k);pack(sy['_phase_state']+72,'H',br);pack(sy['_phase_state']+4,'HHH',0,16,8 if i%2 else 16);pack(a4-0x66da,'h',model.engine_speed(r>>16,k))
   if i%2:
    pack(a4-0x66d8,'HH',v>>16,r>>16);pack(a4-0x66ca,'H',k);pack(sy['_time_scalar_state'],'h',0);pack(sy['_time_scalar_state']+10,'h',0)
  outs=[]
  for j in [0,1]:
   z=run(j,'_phase_prepare_anchor',setup=setup);outs.append((read(a4-0x66da,6),read(a4-0x66ca,2),read(a4-0x66ef,1),read(z[0]['_time_scalar_state']+4,6)))
  assert outs[0]==outs[1],(v,r,k,br)
 counts['prepare_anchor']=5000
 for i in range(10000):
  rate=rng.choice([0,0,0,rng.randint(-1073676288,1073676288)]);n=rng.choice([0,1,7,8,9,16,255,32767,32768,65535]);angle=rng.choice([0,720,-720,2160,-2160,rng.randint(-32768,32767)]);last=rng.choice([angle,angle-1440,angle+1440,0]);last=(last+32768)%65536-32768;carry=rng.choice([0,0,rng.randint(-65535,65535)])
  def setup(sy):
   reg(1,0x470000);reg(2,0x470010);pack(0x470000,'ih',carry,last);pack(0x470010,'h',angle);pack(sy['_time_scalar_fields'],'H',n)
  outs=[]
  for j in [0,1]:
   z=run(j,'_contact_integrate_rate',[rate],setup);outs.append((read(0x470000,6),read(0x470010,2),z[2][:6]+z[2][7:]))
  assert outs[0]==outs[1],(rate,n,angle,last,carry,outs)
 counts['contact_rate']=10000
 for i in range(5000):
  v=rng.randrange(2001*64)*1024;rpm=rng.randrange(6501)*65536;gear=rng.randint(1,4);skid=rng.choice([0,0,0,1]);tr=rng.choice([[16384,0,0,16384],[rng.randint(-16384,16384) for _ in range(4)]]);pack(a4-0x6bb8,'4h',*tr)
  whole=v>>16;pp=whole+(whole>>1);syaw,cyaw,spitch,cpitch=tr;zz=(pp*cpitch)>>14;xyz=[(zz*syaw)>>14,(pp*spitch)>>14,(zz*cyaw)>>14]
  def setup(sy):
   write(sy['_phase_state'],bytes(78));pack(sy['_phase_state']+16,'I',v);pack(sy['_phase_state']+24,'I',rpm);pack(sy['_phase_state']+76,'H',skid);write(sy['_projection_state'],b'X'*36);write(sy['_time_scalar_state'],b'X'*16);write(sy['_drivetrain_state'],b'X'*16)
   pack(a4-0x66d8,'HH',v>>16,rpm>>16);pack(a4-0x66ca,'H',gear);pack(a4-0x66e2,'3h',*xyz);pack(a4-0x6704,'3i',123456,-33,99999)
  outs=[]
  for j in [0,1]:
   z=run(j,'_phase_published',setup=setup);assert all(z[1][k]==z[2][k] for k in range(16) if k not in [0,1,7,8,9])
   outs.append(tuple(read(z[0][name],size) for name,size in [('_phase_state',78),('_projection_state',36),('_time_scalar_state',16),('_drivetrain_state',16)]))
  assert outs[0]==outs[1],(v,skid,tr,outs)
 counts['phase_published']=5000
 for i in range(5000):
  vel,frac,accel=(0,0,0) if i%2 else (rng.randint(-32768,32767),rng.randint(-7,7),rng.randint(-32768,32767));carry=rng.randint(-127,127);n=rng.choice([0,1,8,9,255,32767,32768,65535,rng.randrange(65536)])
  a=run(0,'_motion_fall_displacement',[vel,frac,accel,carry,n]);b=run(1,'_motion_fall_displacement',[vel,frac,accel,carry,n]);assert all(a[2][k]==b[2][k] for k in range(16) if k!=6),(vel,frac,accel,carry,n)
 counts['fall_displacement']=5000
 for i in range(10000):
  active=i%2;n=8 if active else rng.randrange(65536);rpm=rng.randrange(6501);vel=rng.randrange(2001);gear=rng.randint(1,4);delta=rng.randint(-32768,32767);carry=0 if active else rng.randint(-7,7)
  for name in ['_time_velocity_add','_time_rpm_delta']:
   def setup(sy):
    reg(6,0x470020);pack(0x470008,'12h',*([delta]*12));pack(a4-0x66d8,'HH',vel,rpm);pack(a4-0x66ca,'H',gear);write(sy['_time_scalar_state'],bytes(16));pack(sy['_time_scalar_state'],'hH',carry,vel);pack(sy['_time_scalar_state']+10,'hHH',carry,rpm,gear);pack(sy['_phase_state']+2,'H',active);pack(sy['_time_scalar_fields'],'H',n)
   outs=[]
   for j in [0,1]:
    z=run(j,name,[delta],setup);outs.append(([z[2][k] for k in range(16) if k not in ([0,6,9] if active else [6])],read(a4-0x66d8,4),(read(z[0]['_time_scalar_state']+4,6) if active else read(z[0]['_time_scalar_state'],16))))
   assert outs[0]==outs[1],(name,active,n,rpm,vel,gear,delta,carry,outs)
 counts['scalar_hooks']=20000
 for i in range(10000):
  val=rng.choice([0,rng.randint(-1073676288,1073676288)]);factor=rng.choice([0,16384,-16384,rng.randint(-16384,16384)])
  a=run(0,'_contact_project_q16',[val,factor]);b=run(1,'_contact_project_q16',[val,factor]);assert all(a[2][k]==b[2][k] for k in range(16) if k!=6),(val,factor)
 counts['contact_projection']=10000
 for i in range(5000):
  vel=rng.choice([0,0,rng.randint(-32768,32767)]);last=rng.choice([0,vel,rng.randint(-32768,32767)]);carry=rng.choice([0,rng.randint(-7,7)]);accel=rng.choice([0,rng.randint(-32768,32767)]);poscarry=rng.randint(-127,127);n=rng.randrange(65536)
  def setup(sy):
   write(sy['_motion_state'],bytes(32));write(sy['_motion_position_state'],bytes(20));pack(a4-0x66f2,'h',vel);pack(sy['_motion_state']+18,'hh',carry,last);pack(sy['_motion_state']+30,'h',accel);pack(sy['_motion_position_state']+12,'i',poscarry);pack(a4-0x6700,'i',1234);pack(sy['_time_scalar_fields'],'H',n)
  outs=[]
  for j in [0,1]:
   z=run(j,'_motion_fall_position',setup=setup);outs.append((z[2][:6]+z[2][7:],read(z[0]['_motion_state'],32),read(z[0]['_motion_position_state'],20),read(a4-0x6700,4)))
  assert outs[0]==outs[1],(vel,last,carry,accel,poscarry,n,outs)
 counts['fall_position']=5000
 for i in range(1000):
  visible=rng.choice([0,0,rng.randrange(256)]);remaining=rng.choice([0,0,rng.randrange(2041)]);last=rng.choice([0,visible,rng.randrange(256)]);n=rng.randrange(256);vec=[rng.randint(-300,300) for _ in range(3)];carries=[rng.randint(-7,7) for _ in range(3)]
  def setup(sy):
   pack(a4-0x66ee,'B',visible);pack(sy['_motion_drift_state'],'HH3hh',remaining,last,*carries,0);pack(a4-0x66f8,'3h',*vec);pack(a4-0x6704,'3i',123,456,789);pack(sy['_time_scalar_fields'],'H',n)
  outs=[]
  for j in [0,1]:
   z=run(j,'_motion_drift',setup=setup);outs.append((z[2][:6]+z[2][7:],read(z[0]['_motion_drift_state'],12),read(a4-0x66ee,1),read(a4-0x6704,12)))
  assert outs[0]==outs[1],(visible,remaining,last,n,vec,carries,outs)
 counts['drift']=1000
 for i in range(20000):
  rate=rng.choice([-2,2,rng.randint(-3,3)]);n=rng.choice([0,1,7,8,9,32768,65535,rng.randrange(65536)]);carry=rng.randint(-65535,65535)
  a=run(0,'_time_scale_q16',[rate,n,carry]);b=run(1,'_time_scale_q16',[rate,n,carry]);assert all(a[2][k]==b[2][k] for k in range(16) if k!=6),(rate,n,carry,a,b)
 counts['scale_q16']=20000
 for i in range(10000):
  throttle=rng.randint(-128,127);ratio=rng.choice([(7,450),(8,600),(9,750),(10,800)]);mode=rng.randrange(3);valid=rng.randrange(2);oldth=rng.choice([throttle,rng.randint(-128,127)]);oldratio=rng.choice([ratio,(1,2)]);answer=rng.getrandbits(32);first=rng.randrange(65536)
  def setup(sy):
   reg(3,0x470000);reg(6,0x470100);pack(0x470000,'2h',*ratio);pack(0x4700f2,'H',1234);pack(a4-0x66e4,'b',throttle);pack(sy['_drivetrain_state']+6,'H',mode);pack(sy['_drivetrain_power_state'],'2hhHIHHII',*oldratio,oldth,valid,answer,first,0,13,17)
  outs=[]
  for j in [0,1]:
   z=run(j,'_drivetrain_power',setup=setup);outs.append(([v for k,v in enumerate(z[2]) if k not in [0,6,9]],read(z[0]['_drivetrain_power_state'],24),read(0x4700f2,2)))
  assert outs[0]==outs[1],(throttle,ratio,mode,valid,oldth,oldratio,answer,first,outs)
 counts['power_wrapper']=10000
 for i in range(10000):
  vel=rng.choice([-32768,-21844,-21843,-21842,0,21842,21843,21844,32767,rng.randint(-32768,32767)]);frac=rng.randint(-7,7);tr=[rng.randint(-16384,16384) for _ in range(4)];pack(a4-0x6bb8,'4h',*tr);xyz=run(0,'_projection_integer_components',[vel])[2][8:11]
  def setup(sy):
   reg(1,0x480000);write(0x480000,b'X'*12);pack(a4-0x66d8,'h',vel);pack(a4-0x66e2,'3H',*[v&65535 for v in xyz])
  outs=[]
  for j in [0,1]:
   z=run(j,'_projection_quantized_components',[frac],setup);outs.append((z[2][:6]+z[2][7:],read(0x480000,12)))
  assert outs[0]==outs[1],(vel,frac,tr,outs)
 counts['quantized_projection']=10000
 report=dict(passed=True,actual_68000_old_new_cases=counts,total=sum(counts.values()));Path('tmp/p4-first-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
