"""Observe straight motion; optional read-only verification of a guest-initialized throttle probe."""
import argparse,json,os,re,shutil
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--custom1',type=int,default=1);p.add_argument('--delay',type=int,default=0);p.add_argument('--fields',type=int,default=600);p.add_argument('--timing',action='store_true');p.add_argument('--terrain',action='store_true');p.add_argument('--native-pose',action='store_true');p.add_argument('--collision-objects',action='store_true');p.add_argument('--sweep-world',action='store_true');p.add_argument('--phase-inputs',action='store_true');p.add_argument('--initial-throttle',type=int);p.add_argument('--slave',default='s4-straight-current.slave');a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4']
 def g(off,t='short'):return f'*({t}*){a4+off-65536:#x}'
 cols=['landing_crash','field','x8','y8','z8','velocity','fall_velocity','heading','throttle','buttons','braking','mask','road']
 expr=[g(0x9606,'unsigned char'),'$f']+[g(i,'int') for i in [0x98fc,0x9900,0x9904]]+[g(0x9928),g(0x990e),g(0x994a),g(0x991c,'unsigned char'),g(0x95f6,'unsigned short'),g(0x9911,'unsigned char'),g(0x9910,'unsigned char'),g(0xe94a,'unsigned char')]
 if a.terrain:
  cols+=['road_cursor','stunt_base','predicted_pitch','wheel_fl','wheel_fr','wheel_rl','wheel_rr','pitch_rate','roll_rate']
  expr += [g(i,'unsigned int') for i in [0x98e4,0x9952]]+[g(i) for i in [0x994c,0x947e,0x9480,0x9482,0x9484,0x9916,0x9914]]
 if a.native_pose:
  assert not a.phase_inputs
  cols+=['pitch','roll','gear','rpm'];expr += [g(i) for i in [0x9946,0x9948,0x9936,0x992a]]
 if a.timing:
  assert a.custom1
  hits={}
  for bank,b in s.dump_banks('timing-state'):
   for sig in [b'HDDISP01',b'HDSCAL01',b'HDVPROJ1',b'HDPOSST1',b'HDDRIVE1',b'HDSWEEP1',b'HDPHASE1',b'HDMOTN01',b'HDCRATE1']:
    index=b.find(sig)
    if index>=0:
     assert sig not in hits;hits[sig]=bank+index+8
  assert all(k in hits for k in [b'HDDISP01',b'HDSCAL01',b'HDVPROJ1',b'HDPOSST1'])
  def mem(addr,t='int'):return f'*({t}*){addr:#x}'
  ds,ss,vs,ps=[hits[k] for k in [b'HDDISP01',b'HDSCAL01',b'HDVPROJ1',b'HDPOSST1']]
  if a.terrain:
   cols+=['pitch_rate_q16','roll_rate_q16'];expr += [mem(hits[b'HDCRATE1']+i) for i in [8,0]]
  cols+=['consumed','serial','interval','velocity_carry','velocity_last','projected_x','fraction_x','position_fraction_x','position_carry_x','gear','automatic']
  expr += [mem(ds+4),mem(ds+8),mem(ss-10,'unsigned short'),mem(ss,'short'),mem(ss+2,'short'),g(0x991e),mem(vs),mem(vs+24),mem(ps+8),g(0x9936),g(0x993e,'unsigned char')]
 if a.timing and b'HDPHASE1' in hits:
  ph=hits[b'HDPHASE1']
  for name,offset,typ in [('phase_valid',0,'unsigned short'),('phase',4,'unsigned short'),('phase_anchor_v',12,'int'),('phase_current_v',16,'int'),('phase_anchor_r',20,'int'),('phase_current_r',24,'int'),('phase_forecast',28,'int'),('phase_calls',52,'int'),('phase_frames',56,'int')]:
   cols.append(name);expr.append(mem(ph+offset,typ))
 if a.timing and b'HDSWEEP1' in hits:
  sw=hits[b'HDSWEEP1'];cols+=['sweep_active','sweep_tests','sweep_hits','sweep_overflow']
  expr += [mem(sw+50,'unsigned short')]+[mem(sw+i) for i in (54,58,62)]
  if a.sweep_world:
   cols+=['sweep_scanned','sweep_rejected'];expr += [mem(sw+i) for i in (74,78)]
   cols += ['course_current','course_next','checkpoint_latch','lap_clock']
   expr += [g(i,'unsigned int') for i in (0xadcc,0xadd0)]+[g(0xaf30,'unsigned char'),g(0x9790,'unsigned int')]
 if a.phase_inputs:
  assert a.timing and b'HDPHASE1' in hits
  cols += ['gear_request','joystick_gear']
  expr += [g(i,'unsigned char') for i in (0x991d,0x95ff)]
  cols += ['fall_carry','fall_last','fall_accel','crash']
  expr += [mem(hits[b'HDMOTN01']+i,'short') for i in (18,20,30)]+[g(0x9606,'unsigned char')]
  cols+=['rpm','skid','turning','pitch','roll'];expr += [g(0x992a),g(0xaf31,'unsigned char'),g(0xf790,'unsigned char'),g(0x9946),g(0x9948)]
  cols+=['throttle_carry','throttle_last'];expr += [mem(ss+4),mem(ss+8,'unsigned char')]
  cols+=['spin','spin_carry','spin_last','grade_disabled'];expr += [g(0x991a),mem(hits[b'HDMOTN01']+24),mem(hits[b'HDMOTN01']+28,'short'),g(0xf791,'unsigned char')]
  for axis in [0,1,2]:
   cols += [f'held_vector_{axis}',f'held_fraction_{axis}'];expr += [g(0x991e+axis*2),mem(vs+axis*4)]
  cols += ['sin_yaw','cos_yaw','sin_pitch','cos_pitch'];expr += [g(i) for i in [0x9448,0x944a,0x944c,0x944e]]
  for axis in [1,2]:
   cols += [f'position_fraction_{axis}',f'position_carry_{axis}'];expr += [mem(vs+24+4*axis),mem(ps+8+4*axis)]
 lines=[f'gdb break *{base+0x3f2:#x}',f'break *{base+0xcdb0:#x}','set $f=0',f'while $f<{a.fields}','continue',f'if $pc=={base+0x3f2:#x}','set $f=$f+1','end']
 if a.initial_throttle is not None:
  assert a.timing and 1<=a.initial_throttle<=100
  lines.insert(1,f'break *{base+0xb662:#x}')
  lines.insert(lines.index('set $f=0'),'set $initialized=0')
  at=lines.index('continue')+1
  original=mem(hits[b'HDDRIVE1'],'unsigned short') if b'HDDRIVE1' in hits else mem(ss-10,'unsigned short')
  init_expr=['$f',mem(ds+4),original,g(0x98fc,'int'),g(0x9900,'int'),g(0x9904,'int'),g(0x9928),mem(ss,'short'),g(0x992a),g(0x9936),g(0x993e,'unsigned char'),g(0x991c,'unsigned char')]
  lines[at:at]=[f'if $pc=={base+0xb662:#x} && $initialized==0 && {g(0x991c,"unsigned char")}>0','printf "INIT '+' '.join(['%d']*len(init_expr))+'\\n",'+','.join(init_expr),'set $initialized=1','end']
 if a.phase_inputs:
  lines.insert(1,f'break *{base+0xcdb6:#x}');lines.insert(1,f'break *{base+0xcdbe:#x}')
 for tag,off in [('VBL',0x3f2),('STEP',0xcdb0)]+([('INPUT',0xcdb6),('INTEGRATED',0xcdbe)] if a.phase_inputs else []):lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
 if a.collision_objects:
  collision_cols=['field','site','object','world_x','world_y','world_z','type','class','active','traffic_base','traffic_count']
  collision_expr=['$f','$pc-'+str(base),'$a3']+[f'*(short*)($a3+{i})' for i in [8,10,12]]+[f'*(unsigned char*)($a3+{i})' for i in [25,28,30]]+[g(0xaf06,'unsigned int'),g(0xaf04)]
  for off in [0xbc62,0xbd40]:
   lines.insert(1,f'break *{base+off:#x}')
   lines += [f'if $pc=={base+off:#x}','printf "COLLISION '+' '.join(['%d']*len(collision_expr))+'\\n",'+','.join(collision_expr),'end']
 lines+=['end','delete'];reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 if a.collision_objects:
  collision_rows=[dict(zip(collision_cols,map(int,v.split()))) for v in re.findall(r'^COLLISION ([-0-9 ]+)$',reply,re.M)]
  (out/'collision-objects.json').write_text(json.dumps(collision_rows,indent=2)+'\n')
 if a.initial_throttle is not None:
  initial=[list(map(int,v.split())) for v in re.findall(r'^INIT ([-0-9 ]+)$',reply,re.M)]
  assert len(initial)==1
  field,consumed,interval,x,y,z,velocity,carry,rpm,gear,automatic,old_throttle=initial[0]
  assert (x,y,z,velocity,carry,gear,automatic,old_throttle)==(213368,0,200224,0,0,1,1,a.initial_throttle),initial
  initialization=dict(scope='Read-only verification of VERIFY_STEPINPUT_INITIAL_THROTTLE guest initialization. Not the unchanged input tape or a controls test.',field=field,consumed_before=consumed-interval,initial_interval=interval,position=[x,y,z],velocity=velocity,velocity_carry=carry,rpm=rpm,gear=gear,automatic=automatic,old_throttle=old_throttle,new_throttle=a.initial_throttle)
 rows=[dict(kind=k,**dict(zip(cols,map(int,v.split())))) for k,v in re.findall(r'^(VBL|STEP|INPUT|INTEGRATED) ([-0-9 ]+)$',reply,re.M)]
 assert sum(r['kind']=='VBL' for r in rows)==a.fields
 if a.initial_throttle is not None:
  initialization['valid']=all(r['throttle']==a.initial_throttle and r['buttons']==0 for r in rows if r['field']>field)
  (out/'initialization.json').write_text(json.dumps(initialization,indent=2)+'\n')
  assert initialization['valid'], 'Initialized throttle did not remain held with neutral input'
 (out/'motion.json').write_text(json.dumps(dict(profile=a.profile,custom1=a.custom1,delay=a.delay,rows=rows),indent=2)+'\n');(out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n')
 steps=[r for r in rows if r['kind']=='STEP'];print(a.name,'steps',len(steps),'samples',steps[::max(1,len(steps)//8)],flush=True)
finally:s.close()
