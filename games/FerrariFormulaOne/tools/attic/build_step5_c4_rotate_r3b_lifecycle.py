from pathlib import Path
import os,ast
r=Path(__file__).resolve().parents[1];kind=os.environ.get('C1_FIXTURE','reload')
s=(r/'tools/build_step5_c4_rotate_r3b_ab.py').read_text()
coarse=(r.parents[1]/'Games/FerrariFormulaOne_Coarse.s').read_text();install=(r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text()
if kind=='exit':
 body='''C1Fixture:
 move.l C1Completed(pc),d0
 cmpi.l #10,d0
 bne.b .done
 move.w #1,$66be0
.done: rts
'''
elif kind=='contact':
 body='C1Fixture: rts\nC2ContactInput:\n movem.l d0-d7/a0-a6,-(sp)\n move.w sr,-(sp)\n move.l C1Completed(pc),d0\n cmpi.l #10,d0\n blo.b .done\n cmpi.l #20,d0\n bhs.b .done\n tst.w $32fbc\n bne.b .done\n lea C2Injections(pc),a0\n addq.l #1,(a0)\n move.w $32fca,d0\n add.w d0,d0\n lea $1c914,a0\n move.w (a0,d0.w),d0\n neg.w d0\n subi.w #80,d0\n move.w d0,$32fc2\n.done:\n move.w (sp)+,ccr\n movem.l (sp)+,d0-d7/a0-a6\n move.w $32fbc,d0\n rts\nC2Wall:\n move.w sr,-(sp)\n move.l a0,-(sp)\n lea C2WallHits(pc),a0\n addq.l #1,(a0)\n move.l (sp)+,a0\n move.w (sp)+,ccr\n link a6,#-16\n movem.l d2,-(sp)\n jmp $69894\nC2Injections: dc.l 0\nC2WallHits: dc.l 0\n'
 install=install.replace(' bsr.w FF1InstallPresentation',' cmpi.l #$4e56fff0,$6988c\n bne.w C1Fault\n cmpi.l #$48e72000,$69890\n bne.w C1Fault\n lea C2Wall(pc),a0\n move.w #$4ef9,$6988c\n move.l a0,$6988e\n move.w #$4e71,$69892\n bsr.w FF1InstallPresentation',1)
elif kind=='images':
 body='C1Fixture: rts\n'
 coarse=coarse.replace(' tst.l d0\n bne.b .behind',' tst.l d0\n ; Image fixture: draw every admitted update.',1)
elif kind=='ownership':
 body="""C1Fixture:
 move.l C1Completed(pc),d0
 cmpi.l #1,d0
 bne.w .done
 ; Freeze real VBL delivery while injecting a deterministic paused interval.
 move.l $4.w,a6
 jsr -120(a6)
 lea C1Context(pc),a0
 bsr.w FF1TimeDue
 lea C4DebtBefore(pc),a1
 move.l d2,(a1)+
 move.l d1,(a1)
 ; Activation acquired the enabled BLIT bit.
 move.w C4BlitOwned(pc),d0
 cmpi.w #64,d0
 bne.w C1Fault
 bsr.w FF1C4BlitAcquire
 move.w C4BlitOwned(pc),d0
 cmpi.w #64,d0
 bne.w C1Fault
 ; Exercise the actual pause/resume hooks; stub only the native input wait.
 move.w $2546a,d2
 move.w #$4e75,$2546a
 bsr.w C1Pause
 move.w d2,$2546a
 lea C1Context(pc),a0
 cmpi.l #1,FF1T_PAUSED(a0)
 bne.w C1Fault
 moveq #19,d7
.paused_fields:
 bsr.w FF1TimeField
 dbra d7,.paused_fields
 bsr.w FF1TimeDue
 tst.l d0
 bne.w C1Fault
 cmp.l C4DebtBefore(pc),d2
 bne.w C1Fault
 cmp.l C4DebtBefore+4(pc),d1
 bne.w C1Fault
 bsr.w FF1TimeConsume
 cmpi.l #-1,d0
 bne.w C1Fault
 move.w C4BlitOwned(pc),d0
 bne.w C1Fault
 move.w $dff01c,d0
 andi.w #64,d0
 beq.w C1Fault
 bsr.w C1Resume
 lea C1Context(pc),a0
 tst.l FF1T_PAUSED(a0)
 bne.w C1Fault
 bsr.w FF1TimeDue
 cmp.l C4DebtBefore(pc),d2
 bne.w C1Fault
 cmp.l C4DebtBefore+4(pc),d1
 bne.w C1Fault
 lea C4DebtPassed(pc),a1
 move.l #1,(a1)
 move.w C4BlitOwned(pc),d0
 cmpi.w #64,d0
 bne.w C1Fault
 move.w $dff01c,d0
 andi.w #64,d0
 bne.w C1Fault
 ; Releasing twice must restore exactly once.
 bsr.w FF1C4BlitRestore
 bsr.w FF1C4BlitRestore
 move.w $dff01c,d0
 andi.w #64,d0
 beq.w C1Fault
 move.w C4BlitOwned(pc),d0
 bne.w C1Fault
 ; An initially disabled bit must stay disabled after acquire/release.
 move.w #64,$dff09a
 bsr.w FF1C4BlitAcquire
 move.w C4BlitOwned(pc),d0
 bne.w C1Fault
 bsr.w FF1C4BlitRestore
 move.w $dff01c,d0
 andi.w #64,d0
 bne.w C1Fault
 ; Return to race ownership, including the pending-completion case.
 move.w #$8040,$dff09c
 move.w #$8040,$dff09a
 bsr.w FF1C4BlitAcquire
 move.w C4BlitOwned(pc),d0
 cmpi.w #64,d0
 bne.w C1Fault
 move.w $dff01c,d0
 andi.w #64,d0
 bne.w C1Fault
 lea C4OwnershipPassed(pc),a0
 move.l #1,(a0)
 move.l $4.w,a6
 jsr -126(a6)
.done:
 rts
C4OwnershipPassed: dc.l 0
C4DebtPassed: dc.l 0
C4DebtBefore: dc.l 0,0
"""
elif kind in ('fault','motion-fault'):
 body="""C1Fixture:
 move.l C1Completed(pc),d0
 cmpi.l #10,d0
 beq.w C1Fault
 rts
"""
 if kind=='motion-fault':body=body.replace('beq.w C1Fault','beq.w velocity_fault')
elif kind=='reload':
 old=ast.parse((r/'tools/build_step5_b7_reload_v3.py').read_text());patch=next(ast.literal_eval(n.value) for n in old.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='patch' for t in n.targets))
 body=ast.literal_eval(ast.parse(patch).body[0].value.args[1]).replace('FF1PresentationAfterTick:', 'C1Fixture:',1).replace('schedule_completed','C1Completed').replace(' cmpi.l #10,C1Completed(pc)',' move.l C1Completed(pc),d0\n cmpi.l #10,d0').replace(' tst.l public_reload_count(pc)',' move.l public_reload_count(pc),d0')
 body=body.replace('bsr.l','bsr.w').replace('(public_reload_count.l,pc)','public_reload_count(pc)').replace('(public_reload_old.l,pc)','public_reload_old(pc)').replace('(public_reload_size.l,pc)','public_reload_size(pc)').replace('(public_reload_hold.l,pc)','public_reload_hold(pc)')
 body+='\npublic_reload_count: dc.l 0\npublic_descriptor: dc.l 0\npublic_reload_old: dc.l 0\npublic_reload_size: dc.l 0\npublic_reload_hold: ds.l 2\n'
 install=install.replace(' move.l a4,a2',' lea public_descriptor(pc),a0\n move.l a3,(a0)\n move.l a4,a2',1).replace(' move.l 160*4(a2),(a0)',' move.l 160*4(a2),(a0)\n lea public_reload_hold(pc),a0\n bsr.w FF1PublicRelease',1)
else:raise ValueError(kind)
coarse=coarse.replace('C1Checkpoint:\n nop','C1Checkpoint:\n bsr.w C1Fixture\n nop',1)+'\n'+body
inject="(o/'FerrariFormulaOne_Coarse.s').write_text("+repr(coarse)+")\n(o/'FerrariFormulaOne_CoarseInstall.s').write_text("+repr(install)+")\n"
if kind=='contact':
 motion=(r.parents[1]/'Games/FerrariFormulaOne_Coarse200Motion.s').read_text().replace('fine_bounds:\n','fine_bounds:\n bsr.w C2ContactInput\n',1)
 inject+="(o/'FerrariFormulaOne_Coarse200Motion.s').write_text("+repr(motion)+")\n"
s=s.replace("exec(compile(s,","s=s.replace('step5-c4-rotate-r3b-v1-ab','step5-c4-rotate-r3b-v1-ab-"+kind+"')\ns=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
