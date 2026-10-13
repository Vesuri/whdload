; SPS 0481 native 100 ms candidate. Default-off: the host must select coarse,
; bind game operands, validate/install patches, flush caches and own their lifetime.
; No player/opponent rate conversion or fractional state is installed.
; The native head still samples input once per admitted update. A service pass
; admits at most two updates; a full pass returns through the native head before
; starting another pass. Debt is never dropped, including during overload.
; FF1_COARSE_020 selects unprivileged CCR saves, otherwise all code is 68000-safe.
 IFD FF1_COARSE_STEP
C1SaveFlags macro
 IFD FF1_COARSE_020
 move.w ccr,-(sp)
 ELSE
 move.w sr,-(sp)
 ENDC
 endm

C1Head:
 movem.l d0-d7/a0-a6,-(sp)
 C1SaveFlags
 lea C1Heads(pc),a0
 addq.l #1,(a0)
 cmpi.l #126,(a0)
 bne.b .existing
 bsr.w C1Activate
.existing:
 move.w C1Active(pc),-(sp)
 tst.w (sp)+
 beq.b .done
 move.w C1Control(pc),-(sp)
 tst.w (sp)+
 bne.b .done
 lea C1Context(pc),a0
.wait:
 bsr.w FF1TimeDue
 tst.l d0
 beq.b .wait
 lea C1Batch(pc),a1
 tst.w (a1)
 bne.b .admit
 move.w #2,(a1)
.admit:
 subq.w #1,(a1)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 move.w $66be0,d0
 jmp $6517a

C1Vbl:
 move.w d1,$24ad2
 movem.l d0-d3/a0-a1,-(sp)
 C1SaveFlags
 lea C1Context(pc),a0
 bsr.w FF1TimeField
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 rts

C1End:
 movem.l d0-d7/a0-a6,-(sp)
 C1SaveFlags
 move.w C1Control(pc),-(sp)
 tst.w (sp)+
 bne.b .control
 lea C1Context(pc),a0
 bsr.w FF1TimeConsume
 IFD FF1_COARSE_200_COMPLETE
 cmpi.l #2,d0
 ELSE
 cmpi.l #1,d0
 ENDC
 bne.w C1Fault
.control:
 lea C1Completed(pc),a0
 addq.l #1,(a0)
 IFD FF1_COARSE_VERIFY
 bsr.w C1Record
 ENDC
C1Checkpoint:
 nop
 clr.w $1c1b4
 move.w C1DrawEnabled(pc),-(sp)
 tst.w (sp)+
 beq.b .done
 move.w C1Control(pc),-(sp)
 tst.w (sp)+
 bne.b .draw
 lea C1Context(pc),a0
 bsr.w FF1TimeDue
 tst.l d0
 bne.b .behind
.draw:
 bsr.w B8Draw
 bra.b .done
.behind:
 lea C1Skipped(pc),a0
 addq.l #1,(a0)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65174

C1NativeEnd:
 movem.l d0-d7/a0-a6,-(sp)
 C1SaveFlags
 lea C1Completed(pc),a0
 addq.l #1,(a0)
 IFD FF1_COARSE_VERIFY
 bsr.w C1Record
 ENDC
C1NativeCheckpoint:
 nop
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jsr $2a130
 jmp $65f34

; Recovery and boost retain native-tenth pulses: one at 100 ms, two at 200 ms.
; The instrument/status renderer is patched to omit only these state writes.
recovery_tick:
 IFD FF1_COARSE_200_COMPLETE
 bsr.w C4RecoveryOnce
C4RecoveryOnce:
 ENDC
 lea $2268e,a0
 moveq #1,d0
 bsr.w FF1AdvanceRecovery
 tst.w $1c21e
 bne.b .done
 lea recovery_simulation(pc),a0
 move.w #1,(a0)
 jsr $6c5c6
 lea recovery_simulation(pc),a0
 clr.w (a0)
.done:
 rts
boost_before:
 moveq #1,d0
 rts
C1RecoveryEntry:
 jmp $6c220
C1RecoveryClear:
 C1SaveFlags
 move.w recovery_simulation(pc),-(sp)
 tst.w (sp)+
 bne.b .simulation
 move.w (sp)+,ccr
 clr.w $6a694
 jmp $6c5e4
.simulation:
 move.w (sp)+,ccr
 jmp $6c5e4
C1RecoveryBody:
 C1SaveFlags
 move.w recovery_simulation(pc),-(sp)
 tst.w (sp)+
 beq.b .presentation
 move.w (sp)+,ccr
 ext.l d0
 asl.l #1,d0
 move.l d0,a0
 jmp $6c5fc
.presentation:
 move.w (sp)+,ccr
 jmp $6c6ea
C1RecoveryDraw:
 C1SaveFlags
 move.w recovery_simulation(pc),-(sp)
 tst.w (sp)+
 bne.b .simulation
 move.w (sp)+,ccr
 move.w -16(a6),d0
 ext.l d0
 jmp $6c6f0
.simulation:
 move.w (sp)+,ccr
 jmp $6c7c0
C1RecoveryExit:
 C1SaveFlags
 move.w recovery_simulation(pc),-(sp)
 tst.w (sp)+
 bne.b .simulation
 move.w (sp)+,ccr
 move.w $6a694,d0
 jmp $6c7ce
.simulation:
 move.w (sp)+,ccr
 movem.l (sp)+,d2-d5
 unlk a6
 rts

; Reversible native pause preserves active debt. Called at native pause edges.
C1Pause:
 movem.l d0-d3/a0-a1,-(sp)
 C1SaveFlags
 lea C1Context(pc),a0
 bsr.w FF1TimePause
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 jsr $2546a
 rts
C1Resume:
 movem.l d0-d3/a0-a1,-(sp)
 C1SaveFlags
 lea C1Context(pc),a0
 bsr.w FF1TimeResume
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 move.w $1c8b0,d0
 rts

C1Exit:
 movem.l d0-d7/a0-a6,-(sp)
 C1SaveFlags
 bsr.w C1Restore
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65f48

C1Unload:
 movem.l d0-d7/a0-a6,-(sp)
 C1SaveFlags
 cmpi.l #$22f30,(a4)
 bne.b .done
 bsr.w C1Restore
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 movem.l d0-d2/a4-a6,-(sp)
 move.l 4(a4),d0
C1UnloadJump:
 jmp $0.l

C1Restore:
 move.l $4.w,a6
 jsr -120(a6)
 lea C1Ledger(pc),a0
 bsr.w FF1PatchRestore
 ; Restore callback runs before the current race allocation may disappear.
 lea C1Active(pc),a0
 clr.w (a0)+
 clr.w (a0)
 lea C1Heads(pc),a0
 clr.l (a0)+
 clr.l (a0)+
 clr.l (a0)
 lea public_bound(pc),a0
 clr.l (a0)
 lea s2_rng_done(pc),a0
 clr.w (a0)
 lea FF1PresentationInstalled(pc),a0
 clr.l (a0)
 lea FF1FlagGraphic(pc),a0
 clr.w (a0)
 lea B8PitMessage(pc),a0
 clr.w (a0)
 bsr.w C1Flush
 move.l $4.w,a6
 jsr -126(a6)
 rts

C1Fault:
 lea error(pc),a0
 move.l #100,(a0)
.stop: bra.b .stop

C1Active: dc.w 0
C1Batch: dc.w 0
C1Control: dc.w 0
C1DrawEnabled: dc.w 1
C1Heads: dc.l 0
C1Completed: dc.l 0
C1Skipped: dc.l 0
error: dc.l 0
recovery_simulation: dc.w 0
 IFD FF1_COARSE_200_COMPLETE
events_pulse: dc.w 2
 ELSE
events_pulse: dc.w 1
 ENDC
 include "FerrariFormulaOne_Time.s"
C1Context: ds.b FF1T_SIZE
 include "FerrariFormulaOne_Logic.s"
 include "FerrariFormulaOne_Presentation.s"
 include "FerrariFormulaOne_RenderOwnership.s"
 include "FerrariFormulaOne_FullPresentation.s"
 ENDC
