from pathlib import Path
r=Path(__file__).resolve().parents[1];t=r/'tools'
# Contact: retain the old 8-car result ABI in fixture-only buffers. Copy only
# player state into/out of the compact live block around the native routine.
s=(t/'build_step5_b3_contacts.py').read_text().replace('step5-b3-contacts-v4','step5-b4-contacts-v3').replace('step5-b3-v4','step5-b4-v3').replace("'-DFF1_PLAN_B=1'","'-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1'")
inject='''
for name in ('position_shadow','velocity_shadow','speed_shadow'):
 extra=extra.replace(name,'fixture_'+name)
before='';after=''
for name,size in [('position_shadow',12),('velocity_shadow',12),('speed_shadow',6)]:
 for off in range(0,size,2):
  before+=f' move.w fixture_{name}+{off}(pc),d0\\n lea {name}+{off}(pc),a0\\n move.w d0,(a0)\\n'
  after+=f' move.w {name}+{off}(pc),d0\\n lea fixture_{name}+{off}(pc),a0\\n move.w d0,(a0)\\n'
extra=extra.replace(' jsr $68d4e',before+' jsr $68d4e'+ '\\n'+after)
extra+='fixture_position_shadow: ds.b 96\\nfixture_velocity_shadow: ds.b 96\\nfixture_speed_shadow: ds.b 48\\n'
'''
s=s.replace("(o/'cases.json').write_text",inject+"\n(o/'cases.json').write_text")
(t/'build_step5_b4_contacts.py').write_text(s)
for tool in ('test','analyze'):
 s=(t/f'{tool}_step5_b3_contacts.py').read_text().replace('b3-contacts-v4','b4-contacts-v3').replace('step5-b3-contact-validation','step5-b4-contact-validation')
 (t/f'{tool}_step5_b4_contacts.py').write_text(s)
# Recovery: the old diagnostic result ABI has zero opponent carries, and one
# live fuel byte; seed all five player carries to 4 and require them untouched.
s=(t/'build_step5_b3_recovery.py').read_text().replace('step5-b3-recovery-v4','step5-b4-recovery-v3').replace('step5-b3-v4','step5-b4-v3').replace("'-DFF1_PLAN_B=1'","'-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1'")
s=s.replace('fr=[4]*8;wr=[4]*8','fr=[4]+[0]*7;wr=[0]*8')
s=s.replace(' lea fuel_remainders(pc),a0\n move.w #4,(a0,d0.l)\n lea wear_remainders+8(pc),a0\n move.w #4,(a0,d0.l)', ' lea fuel_remainders(pc),a0\n move.b #4,(a0)\n lea wear_remainders(pc),a0\n move.l #$04040404,(a0)')
(t/'build_step5_b4_recovery.py').write_text(s)
s=(t/'test_step5_b3_recovery.py').read_text().replace('b3-recovery-v4','b4-recovery-v3').replace('b3-v4-recovery','b4-v3-recovery')
(t/'test_step5_b4_recovery.py').write_text(s)
for typ in ('build','test'):
 s=(t/f'{typ}_step5_b3_counter.py').read_text().replace('b3-v4','b4-v3').replace("'-DFF1_PLAN_B=1'","'-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1'")
 (t/f'{typ}_step5_b4_counter.py').write_text(s)
