from pathlib import Path
p=Path('Games/FerrariFormulaOne_UpdateHooks.s');s=p.read_text()
s=s.replace('; FF1_PLAN_B selects', '; FF1_PLAYER_HOOKS requires FF1_PLAN_B and consolidates player state/hooks.\n; FF1_PLAN_B selects',1)
s=s.replace('velocity_shadow: ds.b 96',''' IFD FF1_PLAYER_HOOKS
; Persistent player state, exactly 64 bytes. Cursor and condition carries are
; unsigned 0..4, so bytes retain their complete domains. The steering helper
; leaves byte 11 (fuel carry) alone. Scratch and saved contact state are separate.
player_state:
velocity_shadow: ds.b 12
position_shadow: ds.b 12
heading_shadow: ds.b 12
speed_shadow: ds.b 6
steering_shadow: ds.b 11
fuel_remainders: ds.b 1
 ds.b 6
wear_remainders: ds.b 4
player_state_end:
 ELSE
velocity_shadow: ds.b 96
 ENDC''')
for decl in ['position_shadow: ds.b 96','heading_shadow: ds.b 96','speed_shadow: ds.b 48','steering_shadow: ds.b 144','wear_remainders: ds.w 12','fuel_remainders: ds.w 8']:
 s=s.replace(decl,' IFND FF1_PLAYER_HOOKS\n'+decl+'\n ENDC')
s=s.replace(' moveq #7,d0\n.init_speed:', ' IFD FF1_PLAYER_HOOKS\n moveq #0,d0\n ELSE\n moveq #7,d0\n ENDC\n.init_speed:')
s=s.replace(' moveq #7,d7\n.init:', ' IFD FF1_PLAYER_HOOKS\n moveq #0,d7\n ELSE\n moveq #7,d7\n ENDC\n.init:')
# Calls are already player-only at B3 guards. Keep D0's original zero result.
for name,shadow in [('velocity_context','velocity_shadow'),('heading_context','heading_shadow'),('bridge_context','position_shadow'),('steering_context','steering_shadow'),('velocity_speed_context','speed_shadow'),('velocity_array_context','velocity_shadow'),('velocity_speed_array','speed_shadow')]:
 s=s.replace(' bsr.w '+name+'\n',' IFD FF1_PLAYER_HOOKS\n lea ('+shadow+'.l,pc),a0\n moveq #0,d0\n ELSE\n bsr.w '+name+'\n ENDC\n')
# The four player tyre recipients still select their own byte, not a car context.
s=s.replace(' bsr.w wear_context\n',' IFD FF1_PLAYER_HOOKS\n move.l a0,d2\n subi.l #$66c52,d2\n lsr.l #2,d2\n lea wear_remainders(pc),a1\n adda.l d2,a1\n ELSE\n bsr.w wear_context\n ENDC\n')
s=s.replace(' bsr.w fuel_context\n',' IFD FF1_PLAYER_HOOKS\n lea fuel_remainders(pc),a1\n ELSE\n bsr.w fuel_context\n ENDC\n')
# Byte carry tracing retains the accepted word-record ABI.
for start,end in [('wear_reset:','wear_installed:'),('fuel_reset:','fuel_installed:')]:
 a=s.index(start);b=s.index(end,a);s0=s[a:b]
 s0=s0.replace(' clr.w (a1)',' IFD FF1_PLAYER_HOOKS\n clr.b (a1)\n ELSE\n clr.w (a1)\n ENDC')
 for off in (20,22):
  s0=s0.replace(f' move.w (a1),{off}(a4)',f' IFD FF1_PLAYER_HOOKS\n clr.w {off}(a4)\n move.b (a1),{off+1}(a4)\n ELSE\n move.w (a1),{off}(a4)\n ENDC')
 s=s[:a]+s0+s[b:]
# No dormant opponent carries exist in the compact candidate; the VERIFY
# snapshot still has the historical eight-word shape with zeros for opponents.
a=s.index(' lea fuel_remainders(pc),a0\n moveq #7,d0\n.fuelcarry:');b=s.index('\n rts',a)
old=s[a:b];s=s[:a]+''' IFD FF1_PLAYER_HOOKS
 clr.w (a1)+
 move.b fuel_remainders(pc),-1(a1)
 moveq #14,d0
.emptycarry:
 clr.w (a1)+
 dbra d0,.emptycarry
 ELSE
'''+old+'\n ENDC'+s[b:]
p.write_text(s)
# Compact-domain helpers keep the old default representation unchanged.
p=Path('Games/FerrariFormulaOne_Steering.s');s=p.read_text()
for old,new in [('clr.w   10(a0)','clr.b   10(a0)'),('move.w  10(a0),d5','move.b  10(a0),d5'),('move.w  d5,10(a0)','move.b  d5,10(a0)')]:
 s=s.replace('        '+old,' IFD FF1_PLAYER_HOOKS\n        '+new+'\n ELSE\n        '+old+'\n ENDC')
p.write_text(s)
p=Path('Games/FerrariFormulaOne_Wear.s');s=p.read_text()
for old,new in [('move.w  (a1),d2','move.b  (a1),d2'),('move.w  d2,(a1)','move.b  d2,(a1)')]:
 s=s.replace('        '+old,' IFD FF1_PLAYER_HOOKS\n        '+new+'\n ELSE\n        '+old+'\n ENDC')
p.write_text(s)
# Freeze the initial candidate in its own build directory.
p=Path('tmp/dev/tools/build_step5_b3.py');s=p.read_text().replace('step5-b3-v4','step5-b4-v1').replace("'-DFF1_PLAN_B=1'","'-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1'")
Path('tmp/dev/tools/build_step5_b4.py').write_text(s)
