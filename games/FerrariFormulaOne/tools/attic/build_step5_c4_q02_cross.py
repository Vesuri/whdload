from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
blocks=[('$68298',6),('$1dc24',64),('$1c21e',2),('$32f30',16),('$32f94',4),('$32fb4',4),('$32fbc',16),('position_shadow',96),('velocity_shadow',96),('fine_cross_pending',4)]
a='QCross:\n movem.l d0-d7/a0-a6,-(sp)\n lea QSaved(pc),a1\n'
for i,(addr,n) in enumerate(blocks):a+=' lea '+addr+('' if addr.startswith('$') else '(pc)')+f',a0\n move.w #{n//2-1},d0\n.save{i}: move.w (a0)+,(a1)+\n dbra d0,.save{i}\n'
a+=''' move.w #$4ef9,$68298
 lea QReturn(pc),a0
 move.l a0,$6829a
 lea writer_results(pc),a4
 moveq #0,d7
.car:
 moveq #0,d5
.pattern:
 moveq #0,d6
.velocity:
 move.w d7,$32fbc
 clr.w $1c21e
 lea $32f30,a0
 moveq #7,d0
.timers: clr.w (a0)+
 dbra d0,.timers
 lea $1dc24,a0
 moveq #0,d0
.angles:
 move.w d5,d1
 beq.b .straight
 move.w #16,d1
 cmpi.w #2,d5
 bne.b .save_angle
 btst #0,d0
 beq.b .save_angle
 neg.w d1
 bra.b .save_angle
.straight: moveq #0,d1
.save_angle: move.w d1,(a0)+
 addq.w #1,d0
 cmpi.w #32,d0
 blo.b .angles
 move.w #10,$32fca
 move.w #10,$32fc2
 move.w #500,$32fc4
 clr.w $32fc6
 clr.l $32fb4
 lea fine_cross_pending(pc),a0
 clr.l (a0)
 move.w d7,d0
 mulu.w #12,d0
 lea position_shadow(pc),a0
 adda.w d0,a0
 move.l #$000a1234,(a0)
 move.w #-3,4(a0)
 move.l #$01f45678,6(a0)
 move.w #2,10(a0)
 lea velocity_shadow(pc),a0
 adda.w d0,a0
 move.w d6,d1
 add.w d1,d1
 lea QVx(pc),a1
 move.w (a1,d1.w),d1
 move.w d1,$32f94
 move.w d1,(a0)
 move.w #$4321,2(a0)
 move.l #$01f42345,4(a0)
 move.w #500,$32f96
 move.l #$fffc0004,8(a0)
 movem.l d0-d7/a0-a6,-(sp)
 bsr.w QEnter
 movem.l (sp)+,d0-d7/a0-a6
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
 move.w $32fc2,(a4)+
 move.w $32fc4,(a4)+
 move.w $32f94,(a4)+
 move.w $32f96,(a4)+
 move.w $32fca,(a4)+
 move.w fine_car_crosses(pc),(a4)+
 move.w $32fc6,(a4)+
 move.w fine_cross_pending(pc),(a4)+
 addq.w #1,d6
 cmpi.w #3,d6
 blo.w .velocity
 addq.w #1,d5
 cmpi.w #3,d5
 blo.w .pattern
 addq.w #1,d7
 cmpi.w #8,d7
 blo.w .car
 lea QSaved(pc),a1
'''
for i,(addr,n) in enumerate(blocks):a+=' lea '+addr+('' if addr.startswith('$') else '(pc)')+f',a0\n move.w #{n//2-1},d0\n.restore{i}: move.w (a1)+,(a0)+\n dbra d0,.restore{i}\n'
a+=''' movem.l (sp)+,d0-d7/a0-a6
 rts
QEnter:
 link a6,#-64
 jmp $67a04
QReturn:
 unlk a6
 rts
QVx:
 dc.w -80,0,80
QSaved:
 ds.b SAVESIZE
writer_results:
 ds.b 2880
''';a=a.replace('SAVESIZE',str(sum(n for _,n in blocks)))
(r/'tools/step5_c4_q02_cross.s').write_text(a)
cases=[dict(car=car,pattern=pattern,vx=vx) for car in range(8) for pattern in range(3) for vx in (-80,0,80)]
(r/'manifest/step5-c4-q02-cross-cases.json').write_text(json.dumps(dict(cases=cases,record_size=40),indent=2)+'\n')
s=(r/'tools/build_step5_c4_divide_frame_r3g_ab.py').read_text().replace('step5-c4-divide-frame-r3g-v1-ab','step5-c4-q02-cross')
inject="import shutil\nshutil.copy(r/'tools/step5_c4_q02_cross.s',o/'qcross.s')\np=o/'FerrariFormulaOne_CoarseInstall.s'\np.write_text((r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text().replace(' bsr.w FF1TimeInit',' bsr.w FF1TimeInit\\n bsr.w QCross'))\n"
s=s.replace('exec(compile(s,',"s=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\ns=s.replace('public_bindings:', ' include \"qcross.s\"\\npublic_bindings:')\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
