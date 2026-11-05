#!/usr/bin/env python3
"""Audit relocated native blocks: instruction bounds, branches and captured bytes."""
from pathlib import Path
import sys, re, json, struct
import capstone
root=Path(__file__).resolve().parents[1]
code=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()[0x28:0x28+0x3a04c]
blocks=[('sim_native_pitch',0xd514,112),('sim_native_roll',0xd5f2,108),('sim_native_heading',0xf974,86),('sim_native_opponent_steering',0xc06e,42),('sim_native_opponent_brake',0xc0ba,36),('sim_native_terrain',0xf842,48),('sim_native_suspension_bias',0x10030,164),('sim_native_suspension_return',0x1011c,262),('sim_native_gear38',0xf29e,72),('sim_native_gear34',0xf310,72),('sim_native_gear_middle',0xf36e,72),('sim_native_wheel',0xcb48,148)]
blocks += [('sim_aux_native_move',0x11b80,100),('sim_aux_native_rotate',0x11c50,32)]
if len(sys.argv)>1 and 'sim_sound_native_consume ' in (Path(sys.argv[1])/'slave.lst').read_text(encoding='latin1'):
 blocks += [('sim_sound_native_consume',0x7984,70)]
if len(sys.argv)>1 and 'sim_camera_native_vertical ' in (Path(sys.argv[1])/'slave.lst').read_text(encoding='latin1'):
 blocks += [('sim_camera_native_vertical',0x7e9c,30),('sim_camera_native_horizontal',0x7f6e,38)]
spans=[("centroid_build",0xc520,8),("centroid_suspension",0xd2f0,8),("centroid_body",0xd346,66),("centroid_floor",0xd414,10),("centroid_xmax",0xd428,8),("centroid_xmin",0xd43c,8),("centroid_zmax",0xd44e,8),("centroid_zmin",0xd462,8),("geometric_yaw",0xd49e,8)]+blocks+[("fragment_birth",0x11a20,8),("fragment_retire",0x11c38,16)]+[("score_autocreate",0x5f56,6),("score_top",0x3558,24),("score_eligibility",0x5f72,42),("score_insert",0x3e02,10),("score_save",0x4028,8),("score_load",0x3956,8),("score_reset",0x39dc,8),("average_accumulate",0xe852,10),("average_finish",0x597e,6),("events_record_player",71296,6),("events_record_opponent",71288,6),("events_local_player",134634,6),("events_local_opponent",134618,6),("events_summary_compare",22842,8),("events_average_test",22880,8),("events_average_divisor",22896,14),("ui_player_pop8",22168,6),("ui_penalty_pop12",22304,8),("ui_opponent_bne",22504,6),("ui_player_pop16",22576,8),("ui_player_beq10",22594,6),("ui_compare",22600,8),("ui_player_pop24",22726,8),("ui_player_beq20",23552,6),("ui_player_pop14",23692,8),("ui_player_beq42",24428,6),("results_summary_copy",0x116aa,8),("results_reset",0xe27c,6),("results_award",0xe976,20),("results_accumulate",0xe994,8),("results_player",0x1161a,16),("results_opponent",0x11632,12),("time_cache_compare_key",0x9332,8),("time_cache_store_key",0x934e,8),("time_sum_consumer",0x770e,8),("time_sum_recorded",0x92f6,8),("time_sum_seek",0x936c,8),("time_sum_producer",0x20ef6,8),("time_format_entry",0x1a46e,8),("history_input_buffer",0x2412,6),("history_producer_limit",0x7c0a,18),("history_consumer_limit",0x775a,18),("history_seek_bound",0xe56e,14),("history_new_race",0xe07a,10),("history_seek_zero",0xe548,8),("history_save",0xe65a,6),("history_restore",0xe5da,6),("history_rotate",0x7d08,8),("modal_enter",0x1a788,6),("history_reset",0x7908,6),("wheel_pass",0xcb06,8),("contact_distance",0xcf9e,8),("opponent_brake_gate",0xc098,8),("alternate_spin",0xfcba,22),("slip_gate",0xfcd0,8),("slip_relax",0xfcee,22),("slip_impulse_fixed",0xc620,6),("slip_impulse_dynamic",0xc9ce,6),("spin_slip_test",0xfd2e,8),("spin_filter_a",0xfbec,32),("spin_filter_b",0xfc2a,32),("spin_inactive",0xfc10,8),("spin_begin",0xf7da,8),("spin_slip",0xfd46,6),("spin_test",0xc3c4,8),("spin_rotate",0xc3e0,6),("skid_loss",0xfd64,6),("engine_decay",0xf4bc,14),("delay5a",0xf5e4,6),("delay5b",0xf6ca,6),("delay30",0xf784,6),("delay10",0xf7a6,6),("extension_capped",0x10234,20),("extension_variable",0x1024a,22),("contact_zero_a",0xcc9e,8),("contact_zero_b",0xd1b0,8),("forward_distance",0xc326,32),("velocity_delta",0xf60c,16),("steering_entry",0x1033a,10)]
if any(n=='sim_sound_native_consume' for n,_,_ in blocks): spans.append(('sound_publish',0x10904,6))
if any(n=='sim_camera_native_vertical' for n,_,_ in blocks): spans += [('camera_x',0x7fa0,8),('camera_z',0x7fd0,8)]
# The optional expanded dialog replaces the six-byte entry assignment and
# returns through the original modal frame; no interior entry targets exist.
mode_menu = len(sys.argv)>1 and 'sim_mode_dialog ' in (Path(sys.argv[1])/'slave.lst').read_text(encoding='latin1')
if mode_menu:
 spans.append(('mode_dialog_entry',0x1aad6,6))
 if 'sim_preferences_load ' in (Path(sys.argv[1])/'slave.lst').read_text(encoding='latin1'):
  spans.append(('preferences_load',0x16c9e,6))
replay_menu = len(sys.argv)>1 and 'sim_replay_load_entry ' in (Path(sys.argv[1])/'slave.lst').read_text(encoding='latin1')
if replay_menu: spans += [('replay_load_entry',0x80ee,8),('replay_init_tail',0xe50e,6),('replay_load_result',0x9e50,6),('replay_save_direct',0x8174,8),('replay_save_dialog',0x1b1b2,8)]
if len(sys.argv)>1 and 'sim_inverted_wheels_stub ' in (Path(sys.argv[1])/'slave.lst').read_text(encoding='latin1'):
 spans.append(('inverted_fixture_wheels',0xc614,6))
md=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_M68K_000)
branches={'bra','bne','beq','bge','bgt','ble','blt','bhi','bls','bcc','bcs','bvc','bvs','bpl','bmi','dbra'}
for name,start,size in spans:
 ins=list(md.disasm(code[start:start+size],start))
 assert sum(i.size for i in ins)==size,(name,'partial instruction')
 for i in ins:
  assert '(pc)' not in i.op_str or (name=='score_autocreate' and i.address==0x5f56 and i.mnemonic=='jsr' and i.op_str=='$38f8(pc)'),(name,'PC-relative data/call',i.address)
  if i.mnemonic.split('.')[0] in branches:
   target=int(i.op_str.rsplit('$',1)[1],16)
   assert start<=target<=start+size or (name=='wheel_pass' and target==0xcc2e) or (name=='replay_load_result' and target==0x9e5a) or (name.startswith('ui_') and target in (0x5842,0x5852,0x5c1a,0x5f9c)),(name,'external branch',i.address,target)
ranges = ((0x3558,0x3574),(0x3e02,0x3fb8),(0x38f8,0x39fa),(0x3fba,0x4038),(0xe852,0xe868),(0x5932,0x598e),(0x20dcc,0x20df0),(0x5698,0x56a2),(0x5720,0x572a),(0x57e8,0x57ee),(0x5830,0x5852),(0x58c6,0x58d4),(0x5c00,0x5c1a),(0x5c8c,0x5caa),(0x5f3e,0x5f9c),(0x1165c,0x116b6),(0xe252,0xe28e),(0xe966,0xe9ae),(0x1160a,0x11640),(0x1a46e,0x1a552),(0x92f2,0x938c),(0x20eee,0x20f18),(0x23b0,0x243c),(0x76dc,0x7770),(0xe06a,0xe0f6),(0xe518,0xe5ee),(0xe5f2,0xe664),(0x7a66,0x7d56),(0x1a784,0x1a7ec),(0x7904,0x7930),(0xbc48,0xc270),(0xc270,0xd8e0),(0xf0d0,0xf7d6),(0xf7d6,0x10012),(0x10012,0x10494))
ranges += ((0x11940,0x11c88),(0x794a,0x80ee),(0x10494,0x1090e))
if mode_menu: ranges += ((0x1aace,0x1ac22),(0x1ac34,0x1ac8e),(0x16c54,0x16cae))
if replay_menu: ranges += ((0x80ee,0x8138),(0xe06a,0xe518),(0x9de0,0x9f28),(0x813e,0x818e),(0x1b0e8,0x1b210))
for start,end in ranges:
 ins=list(md.disasm(code[start:end],start))
 assert sum(i.size for i in ins)==end-start
 for i in ins:
  if i.mnemonic.split('.')[0] not in branches:continue
  target=int(i.op_str.rsplit('$',1)[1],16)
  for name,b,n in spans:
   assert not (b<target<b+n and not b<=i.address<b+n),(name,'incoming branch into displaced body',i.address,target)
if len(sys.argv)>1:
 p=Path(sys.argv[1]);meta=json.loads((p/'anchor.json').read_text());mem=(p/'memory.bin').read_bytes()
 symbols={name:int(addr,16) for name,addr in re.findall(r'^([\w.]+)\s+00:([0-9A-Fa-f]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
 source=(root/'src/4DSportsDrivingHD.s').read_text()
 patch_body=source.split('pl_main\n',1)[1].split('PL_END',1)[0]
 patch_targets=re.findall(r'PL_(?:P|PS|PSS)\s+[^,]+,([A-Za-z_][A-Za-z_0-9]*)',patch_body)
 for target in patch_targets:
  if target in symbols:
   delta=symbols[target]-symbols['pl_main']
   assert -32768<=delta<=32767,(target,'WHDLoad signed patch displacement',delta)
 private=mem.index(b'4DA4PHYS')+12
 base=private-symbols['sim_a4000_private']
 for name,start,size in blocks:
  off=base+symbols[name]
  assert mem[off:off+size]==code[start:start+size],name
  assert mem[off+size:off+size+2]==b'\x4e\x75',name
 if 'sim_score_save_hook' in symbols:
  section=mem[base+symbols['sim_score_save_hook']:base+symbols['sim_score_candidate']]
  assert section.count(code[0x402c:0x4030]+b'\x4e\x75')==1,'native score saving flag clear'
  section=mem[base+symbols['sim_score_eligibility']:base+symbols['sim_score_insert_entry']]
  assert section.count(code[0x5f72:0x5f78])==1,'native finish argument local'
  off=base+symbols['sim_score_insert_entry']
  assert mem[off:off+2]==b'\x58\x8f' and mem[off+2:off+6]==code[0x3e02:0x3e06],'native insertion frame'
 if 'sim_score_load_hook' in symbols:
  section=mem[base+symbols['sim_score_load_hook']:base+symbols['sim_score_reset_hook']]
  assert section.count(code[0x395a:0x395e]+b'\x4e\x75')==1,'native score load result store'
  section=mem[base+symbols['sim_score_reset_hook']:base+symbols['sim_score_record_status']]
  assert section.count(code[0x39e0:0x39e4]+b'\x4e\x75')==1,'native score reset result store'
 if 'sim_average_finish' in symbols:
  section=mem[base+symbols['sim_average_finish']:base+symbols['sim_average_divide']]
  assert section.count(code[0x597e:0x5984]+b'\x4e\x75')==1,'native average division fallback'
  off=base+symbols['sim_average_accumulate']
  assert mem[off:off+6]==code[0xe852:0xe858],'native speed load'
  section=mem[off:base+symbols['sim_average_finish']]
  assert section.count(code[0xe858:0xe85c]+b'\x4e\x75')==1,'native sum update/flags'
 manual=code[0xfbec:0xfc0c]
 assert manual==code[0xfc2a:0xfc4a]
 section=mem[base+symbols['sim_a4000_spin_filter']:base+symbols['sim_a4000_spin_inactive']]
 assert section.count(manual)==1,'manual native spin fallback differs'
 pos=section.index(manual)+len(manual)
 assert section[pos:pos+2]==b'\x4e\x75'
 if 'sim_a4000_spin_alternate' in symbols:
  off=base+symbols['sim_a4000_spin_alternate']
  original=code[0xfcba:0xfcd0]
  section=mem[off:off+160]
  assert section.count(original)==1,'alternate spin native fallback differs'
 if 'sim_a4000_slip_relax' in symbols:
  off=base+symbols['sim_a4000_slip_relax'];section=mem[off:off+160]
  assert section.count(code[0xfcee:0xfd04])==1,'slip native fallback differs'
print(json.dumps({'manual_native_spin_fallback_checked':len(sys.argv)>1,'blocks':len(blocks),'original_bytes':sum(n for _,_,n in blocks),'hook_spans':len(spans),'branch_audit':f'{len(ranges)} instruction ranges','captured_copies_checked':len(sys.argv)>1},indent=2))
