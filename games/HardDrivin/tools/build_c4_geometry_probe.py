"""Private seeded course fixture; never a replacement for VERIFY_DRIVE benchmarks."""
from pathlib import Path
import os,subprocess,shutil,json,hashlib,sys
root=Path.cwd();source=root/'src';dest=root/'tmp/c4-fixture-source';dest.mkdir(exist_ok=True)
for p in source.glob('*.s'):shutil.copyfile(p,dest/p.name)
name=sys.argv[1];scenario=sys.argv[2];params={'collision_follow':(20382,0,17245,0,6),'collision_headon':(20382,0,17445,720,6),'finish':(25000,0,25000,360,0),'checkpoint':(22689,0,16453,-343,6),'loop':(28161,0,14390,-281,4),'loop_follow':(28178,0,14437,-281,4),'jump':(32293,0,18443,-636,2),'jump_clear':(32425,0,18392,-636,2)};x,y,z,yaw,waypoint=params[scenario]
if os.environ.get('C4_MOVING')=='1':
 assert scenario.startswith('collision_')
 yaw=720 if scenario=='collision_follow' else 0
road_segment=100 if scenario.startswith('collision_') else 0 if scenario=='finish' else 60 if scenario=='checkpoint' else 35 if scenario.startswith('loop') else 17
p=dest/'HardDrivinVerify.s';s=p.read_text();needle='\tmove.w #2,(a0)\n.done:';assert needle in s
s=s.replace(needle,'\tbsr _private_c4_seed\n'+needle,1)
s+='\n_private_c4_seed:\n movem.l d0/a0,-(a7)\n'
for off,value,size in [(0x98ea,x,'w'),(0x98ec,y,'w'),(0x98ee,z,'w'),(0x98f6,x,'w'),(0x98f8,y,'w'),(0x98fa,z,'w'),(0x98fc,x*8,'l'),(0x9900,y*8,'l'),(0x9904,z*8,'l'),(0x9944,yaw,'w'),(0x994a,yaw,'w'),(0x9946,0,'w'),(0x9948,0,'w'),(0x994c,0,'w'),(0x994e,0,'w'),(0x9914,0,'w'),(0x9916,0,'w'),(0x991a,0,'w'),(0x990e,0,'w'),(0x9910,15,'b'),(0x9928,int(os.environ.get('C4_VELOCITY','400')),'w'),(0x992a,5000,'w'),(0x992c,int(int(os.environ.get('C4_VELOCITY','400'))*0.28),'w'),(0x9926,int(os.environ.get('C4_VELOCITY','400'))-4,'w'),(0x9936,4,'w'),(0x993e,255,'b'),(0x991c,100,'b'),(0x9950,1,'b')]:
 s+=(f' clr.{size} -${65536-off:x}(a4)\n' if value==0 else f' move.{size} #{value},-${65536-off:x}(a4)\n')
s+=f' movea.l -$66ae(a4),a0\n adda.w #{road_segment*20},a0\n move.l a0,-$671c(a4)\n'
s+=' lea -$68a6(a4),a0\n move.l a0,-$66c0(a4)\n movea.l -$666c(a4),a0\n'
s+=f' adda.w #{waypoint*8},a0\n move.l a0,-$5230(a4)\n movem.l (a7)+,d0/a0\n rts\n'
if os.environ.get('C4_MOVING')=='1':
 s=s.replace('\tbsr _private_c4_seed\n','',1)
 s=s.replace('_verify_step_input:\n','_verify_step_input:\n\tbsr _private_c4_moving_seed\n',1)
 s+='\nPRIVATE_APPROACH_OFFSET equ '+('100' if scenario=='collision_follow' else '-100')+'\n'+Path('tools/c4_moving_collision_seed.s').read_text()
if scenario=='finish':
 s=s.replace(' move.b #1,-$66b0(a4)',' clr.b -$66b0(a4)\n move.b #255,-$50d0(a4)',1)
 s=s.replace(' movea.l -$66ae(a4),a0\n adda.w #0,a0',' movea.l -$6720(a4),a0\n adda.w #0,a0',1)
if scenario=='loop_follow':
 s=s.replace('\tmove.l #(VERIFY_STEPINPUT_X<<16)|200,-$6a06(a4)','\tmove.l #(VERIFY_STEPINPUT_X<<16)|200,-$6a06(a4)\n\tbsr _private_loop_input')
 s+='\n_private_loop_input:\n move.l d0,-(a7)\n move.l -$671c(a4),d0\n sub.l -$66ae(a4),d0\n cmpi.l #37*20,d0\n blo.s .done\n cmpi.l #49*20,d0\n bhs.s .done\n move.w #360,-$6a06(a4)\n.done:\n move.l (a7)+,d0\n rts\n'
s=s.replace(' clr.w -$66ba(a4)\n clr.w -$66b8(a4)\n',' clr.l -$66ba(a4)\n').replace(' clr.w -$66b4(a4)\n clr.w -$66b2(a4)\n',' clr.l -$66b4(a4)\n').replace(' clr.w -$66ec(a4)\n clr.w -$66ea(a4)\n',' clr.l -$66ec(a4)\n')
if os.environ.get('C4_STEER')=='1':
 assert scenario=='loop_follow'
 s=s[:s.index('\n_private_loop_input:')]+'\nPRIVATE_LOOP_AIM equ '+str(int(os.environ.get('C4_LOOP_AIM','26')))+'\n'+Path('tools/c4_loop_steer.s').read_text()
if os.environ.get('C4_FIXED')=='1':
 assert scenario=='loop_follow'
 s=s[:s.index('\n_private_loop_input:')]+'\nPRIVATE_LOOP_MOUSE equ '+str(int(os.environ.get('C4_LOOP_MOUSE','360')))+'\n'+Path('tools/c4_fixed_input.s').read_text()
if os.environ.get('C4_FOLLOW')=='1':
 assert scenario=='loop_follow'
 s=s[:s.index('\n_private_loop_input:')]+Path('tools/'+('c4_racing_input.s' if os.environ.get('C4_RACING_LINE')=='1' else 'c4_follow_input.s')).read_text()
loop_mouse=int(os.environ.get('C4_LOOP_MOUSE','360'));assert 0<=loop_mouse<=639
steering_mouse=int(os.environ.get('C4_MOUSE','320'));assert 0<=steering_mouse<=639
hold_throttle=int(os.environ.get('C4_THROTTLE','100'));assert 0<=hold_throttle<=100
s=s.replace(' move.b #100,-$66e4(a4)',f' move.b #{hold_throttle},-$66e4(a4)')
s=s.replace(' move.w #360,-$6a06(a4)',f' move.w #{loop_mouse},-$6a06(a4)')
p.write_text(s)
flags=['VERIFY_DRIVE','VERIFY_TIME','VERIFY_TIME_SCALARS','VERIFY_TIME_MOTION','VERIFY_TIME_PRESENTATION','VERIFY_TIME_TRAFFIC','VERIFY_TIME_DISPATCH','VERIFY_DISPATCH_CPU','VERIFY_TIME_RECORD','VERIFY_TIME_REPLAY_TIMING','VERIFY_TIME_TIMELINES','VERIFY_TIME_ATTRACT','VERIFY_TIME_PHANTOM','VERIFY_TIME_GHOST_RECORD','VERIFY_TIME_GHOST_PLAYBACK','VERIFY_TIME_GHOST_POST','VERIFY_TIME_INSTRUCTIONS','VERIFY_TIME_AUDIO','VERIFY_TIME_DISSIPATION','VERIFY_DRIVETRAIN_REFERENCE','VERIFY_DRIVETRAIN_SETTLED','VERIFY_DRIVETRAIN_FRACTION','VERIFY_DRIVETRAIN_POSITION','VERIFY_DRIVETRAIN_SQRT','VERIFY_DRIVETRAIN_POWER','VERIFY_DRIVETRAIN_MANUAL','VERIFY_DRIVETRAIN_SKID','VERIFY_DRIVETRAIN_AIR','VERIFY_DRIVETRAIN_PHASE','VERIFY_TIME_SWEEP','VERIFY_STEPINPUT','VERIFY_STEPINPUT_EXACT_THROTTLE','VERIFY_SLOW','VERIFY_GAMEPLAY_SLOW']
if os.environ.get('C4_KEEP_RATE')=='1':
 q=dest/'HardDrivinContact.s';m=q.read_text();needle='_contact_pitch_rate_only:\n\tmovem.l d1-d2/a0-a1,-(a7)'
 assert needle in m
 m=m.replace(needle,needle+'\n IFND VERIFY_DISPATCH_NATIVE\n move.w _time_scalar_fields(pc),d1\n cmpi.w #8,d1\n beq.s .valid_input\n cmpi.w #180,-4(a5)\n bgt.s .done\n cmpi.w #-180,-4(a5)\n blt.s .done\n.valid_input:\n ENDC',1);q.write_text(m)
if os.environ.get('C4_FORCE_RATE'):
 # Experiment: every rear-only contact pass sets the pitch rate to C4_FORCE_RATE units per native step.
 q=dest/'HardDrivinContact.s';m=q.read_text();needle='\tmoveq #0,d2\n\tbsr _contact_response\n\tlea _contact_rates+8(pc),a0'
 assert m.count(needle)==1
 m=m.replace(needle,needle.replace('\tlea','\tmove.l #'+str(int(os.environ['C4_FORCE_RATE'])*65536)+',d1\n\tlea'),1);q.write_text(m)
if os.environ.get('C4_CLAMP')=='1':
 q=dest/'HardDrivinMotion.s';m=q.read_text().replace('_motion_patches:\n\tPL_START','_motion_patches:\n\tPL_START\n\tPL_PS $cba2,_private_contact_clamp',1)
 helper='\n_private_contact_clamp:\n move.w 6(a7),-(a7)\n move.w 6(a7),d0\n move.w _time_scalar_fields(pc),d1\n cmpi.w #8,d1\n beq.s .call\n cmpi.w #180,d0\n ble.s .negative\n move.w #180,d0\n.negative:\n cmpi.w #-180,d0\n bge.s .call\n move.w #-180,d0\n.call:\n move.w d0,-(a7)\n jsr -$7f20(a4)\n addq.w #4,a7\n move.l (a7),4(a7)\n addq.w #4,a7\n rts\n'
 q.write_text(m)
 q=dest/'HardDrivinTime.s';q.write_text(q.read_text()+helper)
if os.environ.get('C4_TERRAIN_ROAD')=='1':
 q=dest/'HardDrivinMotion.s';m=q.read_text().replace('_motion_patches:\n\tPL_START','_motion_patches:\n\tPL_START\n\tPL_P $cdbe,_private_terrain_select\n\tPL_PSS $c1b6,_private_road_selected_hook,2',1);q.write_text(m)
 q=dest/'HardDrivinTime.s';q.write_text(q.read_text()+Path('tools/c4_terrain_road.s').read_text()+Path('tools/c4_road_bounds.s').read_text())
if os.environ.get('C4_ROAD_CONTINUATION')=='1':
 assert os.environ.get('C4_TERRAIN_ROAD')=='1'
 q=dest/'HardDrivinTime.s';m=q.read_text().replace(' tst.b -$16b5(a4)\n bne .native',' tst.b -$16b5(a4)\n bne .native\n move.w _private_road_continuing(pc),d0\n beq .native\n tst.b -$66f0(a4)\n beq .native',1)
 m=m.replace('.road:\n ; Reuse','.road:\n lea _private_road_continuing(pc),a0\n move.w #1,(a0)\n ; Reuse',1)
 m=m.replace('.native:\n movea.l _phase_steering_body(pc),a0','.native:\n lea _private_road_continuing(pc),a0\n clr.w (a0)\n movea.l _phase_steering_body(pc),a0',1);q.write_text(m)
 q=dest/'HardDrivinMotion.s';m=q.read_text().replace('_motion_reset:\n','_motion_reset:\n move.l a0,-(a7)\n lea _private_road_continuing(pc),a0\n clr.w (a0)\n movea.l (a7)+,a0\n',1);q.write_text(m+'\n_private_road_continuing: dc.w 0\n')
if os.environ.get('C4_SUPPORT_OBJECT')=='1':
 assert os.environ.get('C4_TERRAIN_ROAD')=='1'
 q=dest/'HardDrivinTime.s';m=q.read_text();m=m.replace(' tst.b -$16b5(a4)\n bne .native',' tst.b -$16b5(a4)\n bne .objects',1)
 m=m.replace('.native:\n movea.l _phase_steering_body(pc),a0','.objects:\n bsr _private_object_ground\n movea.l _phase_steering_body(pc),a0\n adda.l #$cdda-$b398,a0\n jmp (a0)\n.native:\n movea.l _phase_steering_body(pc),a0',1)
 m+=Path('tools/c4_object_contact.s').read_text()+Path('tools/c4_support_face.s').read_text();q.write_text(m)
if os.environ.get('C4_LANDING_DEPTH')=='1':
 q=dest/'HardDrivinMotion.s';m=q.read_text().replace('_motion_patches:\n\tPL_START','_motion_patches:\n\tPL_START\n\tPL_PS $cc2e,_private_landing_depth',1);q.write_text(m)
 q=dest/'HardDrivinPhase.s';q.write_text(q.read_text()+Path('tools/c4_landing_depth.s').read_text())
if os.environ.get('C4_LANDING_IMPACT')=='1':
 assert os.environ.get('C4_LANDING_DEPTH')!='1'
 q=dest/'HardDrivinMotion.s';m=q.read_text().replace('PL_PS $cc8a,_motion_fall_ground','PL_PS $cc8a,_private_landing_impact',1);q.write_text(m)
 q=dest/'HardDrivinPhase.s';q.write_text(q.read_text()+Path('tools/c4_landing_impact.s').read_text())
if os.environ.get('C4_ROAD_PITCH')=='1':
 q=dest/'HardDrivinMotion.s';m=q.read_text().replace('_motion_patches:\n\tPL_START','_motion_patches:\n\tPL_START\n\tPL_PS $cba2,_private_road_pitch',1);q.write_text(m)
 helper=Path('tools/c4_road_pitch.s').read_text()
 q=dest/'HardDrivinTime.s';q.write_text(q.read_text()+helper)
if os.environ.get('C4_FULL_PITCH')=='1':
 q=dest/'HardDrivinMotion.s';m=q.read_text().replace('PL_PSS $cb6c,_motion_contact_rates,2','PL_PSS $cb6c,_private_full_contact_reset,2').replace('_motion_patches:\n\tPL_START','_motion_patches:\n\tPL_START\n\tPL_PSS $cbb0,_private_full_contact_pitch,6',1);q.write_text(m)
 helper=Path('tools/c4_full_pitch.s').read_text()
 if os.environ.get('C4_WIDE_PITCH')=='1':
  helper=helper.replace(' bne.s .scaled',' bhi.s .scaled',1).replace('_private_full_contact_reset:\n','_private_full_contact_reset:\n move.w _time_scalar_fields(pc),d0\n cmpi.w #8,d0\n bhi.s .wide_reset\n bra _motion_contact_rates\n.wide_reset:\n',1)
 helper+='\n_private_half_gain:\n dc.w '+','.join(str(round((1-2**(-n/8))*65536)) for n in range(136))+'\n'
 q=dest/'HardDrivinTime.s';q.write_text(q.read_text()+helper)
# Large private fixtures can exceed the installer's 16-bit PC reach.
q=dest/'HardDrivinPhase.s';m=q.read_text().replace(' movea.l _resload(pc),a2',' lea _phase_install(pc),a2\n adda.l #_resload-_phase_install,a2\n movea.l (a2),a2',1);q.write_text(m)
if os.environ.get('C3_CHECKPOINT_POST')=='1':
 assert not (source/'HardDrivinCheckpoint.s').exists(), 'Checkpoint query is already integrated; omit private flag'
 q=dest/'HardDrivinDispatch.s';q.write_text(q.read_text().replace('_dispatch_after_physics:\n','_dispatch_after_physics:\n bsr _private_checkpoint_post\n',1))
 q=dest/'HardDrivinTerrain.s';q.write_text(q.read_text()+Path('tools/c3_checkpoint_post.s').read_text())
out=root/'tmp/build'/name
args=[os.environ['VASM'],'-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+str(source),'-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['NDK']]+['-D'+f+'=1' for f in flags]+[f'-DVERIFY_STEPINPUT_X={steering_mouse}',f'-DVERIFY_STEPINPUT_HOLD_THROTTLE={hold_throttle}','-o',str(out.with_suffix('.slave')),'-L',str(out.with_suffix('.lst')),'HardDrivinHD.s']
subprocess.run(args,cwd=dest,check=True)
manifest=dict(steering_mouse=steering_mouse,private_moving_collision=os.environ.get('C4_MOVING')=='1',collision_target=(dict(main_pool_index=96,traffic_index=10,initial_world=[20382,0,17345],type=1,solid_class=8) if scenario.startswith('collision_') else None),seeded_checkpoint_latch=(255 if scenario=='finish' else None),private_checkpoint_post=os.environ.get('C3_CHECKPOINT_POST')=='1',private_road_continuation=os.environ.get('C4_ROAD_CONTINUATION')=='1',private_landing_impact=os.environ.get('C4_LANDING_IMPACT')=='1',private_landing_depth=os.environ.get('C4_LANDING_DEPTH')=='1',private_support_object=os.environ.get('C4_SUPPORT_OBJECT')=='1',private_wide_pitch=os.environ.get('C4_WIDE_PITCH')=='1',private_terrain_road=os.environ.get('C4_TERRAIN_ROAD')=='1',private_racing_line=os.environ.get('C4_RACING_LINE')=='1',private_follow_input=os.environ.get('C4_FOLLOW')=='1',private_road_pitch=os.environ.get('C4_ROAD_PITCH')=='1',private_full_pitch=os.environ.get('C4_FULL_PITCH')=='1',private_keep_rate=os.environ.get('C4_KEEP_RATE')=='1',fixture_all_source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.glob('*.s')},private_contact_clamp=os.environ.get('C4_CLAMP')=='1',scenario=scenario,seed=dict(x=x,y=y,z=z,yaw=yaw,velocity=400,rpm=5000,gear=4,throttle=hold_throttle,road_segment=road_segment,next_stunt_waypoint=waypoint),input_policy=('Road-width racing line from +80 to -80 lateral through loop, transformed to car space; mouse offset twice local X clamped +/-60' if os.environ.get('C4_RACING_LINE')=='1' else 'Next road cross-section in car space; mouse offset twice local X, clamped to +/-60; active segments35..52' if os.environ.get('C4_FOLLOW')=='1' else f'X{loop_mouse} only while native road cursor is loop37..48, otherwise X320' if scenario=='loop_follow' else f'X{steering_mouse}'),scope='One-time pose/dynamics/course-pointer seed at native race initialization. After that only centered steering/held throttle inputs. Geometry is unchanged. The private_contact_clamp field identifies the optional experimental physics wrapper. Not normal-start, input tape, whole lap or benchmark evidence.',source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.s')},fixture_motion_sha256=hashlib.sha256((dest/'HardDrivinMotion.s').read_bytes()).hexdigest(),fixture_verify_sha256=hashlib.sha256((dest/'HardDrivinVerify.s').read_bytes()).hexdigest())
out.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
