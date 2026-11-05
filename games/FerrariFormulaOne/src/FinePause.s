; Same native pause edges as the coarse path. Keep admitted driving debt;
; exclude only the interval spent in the native keyboard wait.
FF1FinePauseInstall:
 cmpi.w #$4eb9,$653fc
 bne.l schedule_bad
 cmpi.l #$2546a,$653fe
 bne.l schedule_bad
 cmpi.w #$3039,$654b8
 bne.l schedule_bad
 cmpi.l #$1c8b0,$654ba
 bne.l schedule_bad
 cmpi.w #$4eb9,$65f48
 bne.l schedule_bad
 cmpi.l #$2a130,$65f4a
 bne.l schedule_bad
 lea (FF1FineExit.l,pc),a0
 move.w #$4ef9,$65f48
 move.l a0,$65f4a
 lea (FF1FinePause.l,pc),a0
 move.l a0,$653fe
 lea (FF1FineResume.l,pc),a0
 move.w #$4eb9,$654b8
 move.l a0,$654ba
 rts
FF1FinePause:
 movem.l d0-d3/a0-a1,-(sp)
 move.w ccr,-(sp)
 lea (schedule_context.l,pc),a0
 bsr.l FF1FineBlitRestore
 bsr.l FF1TimePause
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 jmp $2546a
FF1FineResume:
 movem.l d0-d3/a0-a1,-(sp)
 move.w ccr,-(sp)
 lea (schedule_context.l,pc),a0
 bsr.l FF1TimeResume
 bsr.l FF1FineBlitAcquire
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 move.w $1c8b0,d0
 rts

; Tow branches directly to native cleanup, bypassing the loop-head flag check.
; Restore before any modal cleanup, not merely before the later overlay unload.
FF1FineExit:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.l $4.w,a6
 jsr -120(a6)
 lea (public_patch_context.l,pc),a0
 bsr.l FF1PatchRestore
 bsr.w public_reset
 bsr.w public_flush
 move.l $4.w,a6
 jsr -126(a6)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65f48
