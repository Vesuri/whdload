from pathlib import Path
import json,re
r=Path(__file__).resolve().parents[1];old=(r/'tools/build_step5_native_velocity_contact.py').read_text();ns={'cases':[dict(first=a,second=b,front=f) for a in range(7) for b in range(a+1,8) for f in (0,1)]}
exec(old[old.index("extra='''"):old.index('asm=asm.replace(\'velocity_records')],ns);a=ns['extra'];cases=ns['cases']
# Retain the native contact body and seed both authoritative fractional owners.
seed=''' lea position_shadow(pc),a0
 moveq #0,d6
.position_seed:
 move.w d6,d0
 add.w d0,d0
 lea $6a61a,a1
 move.w (a1,d0.w),(a0)+
 move.w d6,d1
 mulu.w #257,d1
 addi.w #256,d1
 move.w d1,(a0)+
 move.w d6,d1
 subq.w #4,d1
 move.w d1,(a0)+
 lea $6a62a,a1
 move.w (a1,d0.w),(a0)+
 move.w d6,d1
 mulu.w #513,d1
 addi.w #512,d1
 move.w d1,(a0)+
 move.w d6,d1
 subq.w #4,d1
 move.w d1,(a0)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .position_seed
'''
a=a.replace(' movem.l d0-d7/a0-a6,-(sp)\n jsr $68d4e',seed+' movem.l d0-d7/a0-a6,-(sp)\n jsr $68d4e')
a=a.replace(' move.l velocity_swaps(pc),(a4)+',' move.l velocity_swaps(pc),(a4)+\n lea position_shadow(pc),a0\n moveq #23,d6\nsave_position_shadow:\n move.l (a0)+,(a4)+\n dbra d6,save_position_shadow')
a=a.replace(' dbra d6,save_position_shadow',' dbra d6,save_position_shadow\n lea $6f13c,a0\n moveq #3,d6\nsave_native_x:\n move.l (a0)+,(a4)+\n dbra d6,save_native_x')
a=a.replace('contact_results: ds.b '+str(56*148),'contact_results: ds.b '+str(56*260))
blocks=[('$24f60',120),('$6f10a',32),('$32f30',16),('$1c21e',2),('$2268e',16),('$6a60a',48),('$2275a',16),('$6f13c',32),('velocity_shadow',96),('position_shadow',96)]
save=' movem.l d0-d7/a0-a6,-(sp)\n lea QContactSaved(pc),a1\n';restore=' lea QContactSaved(pc),a1\n'
for i,(addr,n) in enumerate(blocks):
 lea=' lea '+addr+('' if addr.startswith('$') else '(pc)')+',a0\n'
 save+=lea+f' move.w #{n//2-1},d0\n.save{i}: move.w (a0)+,(a1)+\n dbra d0,.save{i}\n'
 restore+=lea+f' move.w #{n//2-1},d0\n.restore{i}: move.w (a1)+,(a0)+\n dbra d0,.restore{i}\n'
a=a.replace('contact_fixture:\n','contact_fixture:\n'+save,1).replace('contact_complete:\n bra.b contact_complete','contact_complete:\n'+restore+' movem.l (sp)+,d0-d7/a0-a6\n rts')
a+='QContactSaved: ds.b '+str(sum(n for _,n in blocks))+'\n';a=re.sub(r'(d[0-7])\.l\)',r'\1.w)',a)
(r/'tools/step5_c4_q02_contact.s').write_text(a)
(r/'manifest/step5-c4-q02-contact-cases.json').write_text(json.dumps(dict(cases=cases,record_size=260),indent=2)+'\n')
s=(r/'tools/build_step5_c4_divide_frame_r3g_ab.py').read_text().replace('step5-c4-divide-frame-r3g-v1-ab','step5-c4-q02-contact')
inject="import shutil\nshutil.copy(r/'tools/step5_c4_q02_contact.s',o/'qcontact.s')\np=o/'FerrariFormulaOne_CoarseInstall.s'\np.write_text((r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text().replace(' bsr.w FF1TimeInit',' bsr.w FF1TimeInit\\n bsr.w contact_fixture'))\n"
s=s.replace('exec(compile(s,',"s=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\ns=s.replace('public_bindings:', ' include \"qcontact.s\"\\npublic_bindings:')\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
