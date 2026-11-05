from pathlib import Path
import json,re
r=Path(__file__).resolve().parents[1]
ops=[(0x6993a,0x69940,'offroad_right'),(0x69a0a,0x69a10,'offroad_left'),(0x6998e,0x69994,'offroad_z'),(0x69a5e,0x69a64,'offroad_z'),(0x67a12,0x67a18,'px_sync'),(0x67a26,0x67a2c,'pz_sync'),(0x67a30,0x67a36,'pz_zero'),(0x68306,0x6830c,'px_reset'),(0x68352,0x68358,'px_reset'),(0x68376,0x6837e,'px_350'),(0x683b8,0x683be,'pz_reset'),(0x694c8,0x694ce,'pz_zero'),(0x6956a,0x69570,'px_reset'),(0x68386,0x6838c,'vx_reset'),(0x6e2a4,0x6e2aa,'vz_reset'),(0x6e2ec,0x6e2f2,'vz_reset'),(0x69b36,0x69b3c,'vz_clamp'),(0x69b50,0x69b56,'vz_clamp'),(0x6838c,0x68392,'speed_reset'),(0x694ce,0x694d6,'speed_100'),(0x69b30,0x69b36,'speed_reset'),(0x69b4a,0x69b50,'speed_reset')]
ops=ops[:4]
blocks=[('$2aaa6',2),('$32f94',4),('$32fbc',10),('position_shadow',96),('velocity_shadow',96),('speed_work',6)]
a='QWork:\n movem.l d0-d7/a0-a6,-(sp)\n lea QSaved(pc),a1\n'
for i,(addr,n) in enumerate(blocks):
 a+=' lea '+addr+('' if addr.startswith('$') else '(pc)')+f',a0\n move.w #{n//2-1},d0\n.save{i}: move.w (a0)+,(a1)+\n dbra d0,.save{i}\n'
a+=' lea writer_results(pc),a4\n moveq #0,d7\n.car:\n moveq #0,d5\n.value:\n'
for entry,end,kind in ops:
 a+=f''' bsr.w QSeed
 move.w ${end:x},-(sp)
 move.w #$4e75,${end:x}
 move.w d5,d0
 add.w d0,d0
 lea QValues(pc),a0
 move.w (a0,d0.w),d0
 ext.l d0
 move.w #999,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr ${entry:x}
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,${end:x}
 bsr.w QRecord
'''
a+=' addq.w #1,d5\n cmpi.w #3,d5\n blo.w .value\n addq.w #1,d7\n cmpi.w #8,d7\n blo.w .car\n lea QSaved(pc),a1\n'
for i,(addr,n) in enumerate(blocks):
 a+=' lea '+addr+('' if addr.startswith('$') else '(pc)')+f',a0\n move.w #{n//2-1},d0\n.restore{i}: move.w (a1)+,(a0)+\n dbra d0,.restore{i}\n'
a+=''' movem.l (sp)+,d0-d7/a0-a6
 rts
QSeed:
 move.w #30,$2aaa6
 move.w d7,$32fbc
 move.w #10,$32fc2
 move.w #100,$32fc4
 move.w #7,$32f94
 move.w #200,$32f96
 move.w #50,$32fbe
 lea QSeedPosition(pc),a0
 lea position_shadow(pc),a1
 bsr.w QSeedEight
 lea QSeedVelocity(pc),a0
 lea velocity_shadow(pc),a1
 bsr.w QSeedEight
 lea speed_work(pc),a0
 move.l #$00321111,(a0)
 move.w #3,4(a0)
 rts
QSeedEight:
 moveq #7,d2
.loop:
 move.l (a0),(a1)+
 move.l 4(a0),(a1)+
 move.l 8(a0),(a1)+
 dbra d2,.loop
 rts
QRecord:
 ; Check every non-target owner remains unchanged, not only the target result.
 lea position_shadow(pc),a0
 lea QSeedPosition(pc),a1
 bsr.w QUntouched
 lea velocity_shadow(pc),a0
 lea QSeedVelocity(pc),a1
 bsr.w QUntouched
 move.w d7,d0
 mulu.w #12,d0
 lea position_shadow(pc),a0
 adda.w d0,a0
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 move.l 8(a0),(a4)+
 lea velocity_shadow(pc),a0
 adda.w d0,a0
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 move.l 8(a0),(a4)+
 lea speed_work(pc),a0
 move.l (a0),(a4)+
 move.w 4(a0),(a4)+
 move.w $32fc2,(a4)+
 move.w $32fc4,(a4)+
 move.w $32f94,(a4)+
 move.w $32f96,(a4)+
 move.w $32fbe,(a4)+
 rts
QUntouched:
 moveq #0,d2
.loop:
 cmp.w d7,d2
 beq.b .next
 move.l (a0),d0
 cmp.l (a1),d0
 bne.w QWorkBad
 move.l 4(a0),d0
 cmp.l 4(a1),d0
 bne.w QWorkBad
 move.l 8(a0),d0
 cmp.l 8(a1),d0
 bne.w QWorkBad
.next:
 adda.w #12,a0
 addq.w #1,d2
 cmpi.w #8,d2
 blo.b .loop
 rts
QWorkBad:
 lea error(pc),a0
 move.l #4201,(a0)
 bra.w C1Fault
QValues: dc.w -123,0,321
QSeedPosition: dc.w 10,$1234,-3,100,$5678,2
QSeedVelocity: dc.w 7,$789a,200,$bcde,-4,4
'''
cases=[dict(car=car,value=value,site=hex(entry),kind=kind) for car in range(8) for value in (-123,0,321) for entry,end,kind in ops]
a+='QSaved: ds.b '+str(sum(n for _,n in blocks))+'\nwriter_results: ds.b '+str(len(cases)*40)+'\n'
a=re.sub(r'(\w+:) (dc\.|ds\.)',r'\1\n \2',a)
(r/'tools/step5_c4_q02_work_v2.s').write_text(a)
(r/'manifest/step5-c4-q02-work-v2-cases.json').write_text(json.dumps(dict(cases=cases,record_size=40),indent=2)+'\n')
s=(r/'tools/build_step5_c4_divide_frame_r3g_ab.py').read_text().replace('step5-c4-divide-frame-r3g-v1-ab','step5-c4-q02-work-v2')
inject="import shutil\nshutil.copy(r/'tools/step5_c4_q02_work_v2.s',o/'qwork.s')\np=o/'FerrariFormulaOne_CoarseInstall.s'\np.write_text((r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text().replace(' bsr.w FF1TimeInit',' bsr.w FF1TimeInit\\n bsr.w QWork'))\n"
s=s.replace('exec(compile(s,',"s=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\ns=s.replace('public_bindings:', ' include \"qwork.s\"\\npublic_bindings:')\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))

import re
symbols={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',(o/'fine.list').read_text(),re.M)}
assert -32768 <= symbols['public_bindings']-symbols['FF1VelocityRotate000'] <=32767
