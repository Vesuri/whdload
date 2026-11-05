; Shared bounded diagnostic window, deliberately separate from game hook policy.
; begin: A0=caller-owned Fast buffer, A1=variant data hunk, D0=50/60 Hz.
; Caller validates lifetime, alignment, RAM extent and non-overlap first.
; Null pointers/invalid Hz disable recording. No OS calls or buffer allocation.
; end: freeze first, then header with completed prefix; no file I/O in the game.
; Calls must be serialised on one task. Never invoke frame_stat from an IRQ.
; Every entry preserves registers and CCR. frame_stat takes event.w after return.
recorder_begin:
        movem.l d0/a0-a2,-(sp)
        move.w ccr,-(sp)
        lea timing_active(pc),a2
        clr.w (a2)
        lea frame_stats_count(pc),a2
        clr.l (a2)
        lea frame_stats_dropped(pc),a2
        clr.l (a2)
        lea frame_stats_started(pc),a2
        clr.w (a2)
        lea frame_stats_buffer(pc),a2
        move.l a0,(a2)
        lea timing_data(pc),a2
        move.l a1,(a2)
        cmpa.w #0,a0
        beq.w .done
        cmpa.w #0,a1
        beq.w .done
        cmpi.l #50,d0
        beq.s .valid
        cmpi.l #60,d0
        bne.w .done
.valid:
        lea recorder_hz(pc),a2
        move.l d0,(a2)
        lea timing_active(pc),a2
        move.w #1,(a2)
.done:
        move.w (sp)+,ccr
        movem.l (sp)+,d0/a0-a2
        rts

recorder_end:
        movem.l d0/a0-a1,-(sp)
        move.w ccr,-(sp)
        lea timing_active(pc),a1
        tst.w (a1)
        beq.w .done
        clr.w (a1)
        move.l frame_stats_buffer(pc),a0
        move.l #'WCFS',(a0)+
        move.l recorder_hz(pc),(a0)+
        move.l frame_stats_count(pc),(a0)+
        clr.l (a0)
.done:
        move.w (sp)+,ccr
        movem.l (sp)+,d0/a0-a1
        rts
        cnop 0,4
frame_stats_buffer: dc.l 0
frame_stats_count: dc.l 0
frame_stats_first: dc.l 0
frame_stats_dropped: dc.l 0
recorder_hz: dc.l 0
timing_data: dc.l 0
frame_stats_started: dc.w 0
timing_active: dc.w 0
