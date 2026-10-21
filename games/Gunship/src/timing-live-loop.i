; CUSTOM1-only replacement for the initialized flight call, +0561C.
; Install last: no enhanced flight may start with incomplete isolation hooks.
; a0=arena,a2=resload. Return 0/-1, preserve non-result registers.
timing_loop_install:
 movem.l a0-a3,-(sp)
 move.l _custom1(pc),d0
 beq .disabled
 cmpi.l #1,RT_READY(a0)
 bne .bad
 cmpi.w #1,RT_DRAW_READY(a0)
 bne .bad
 movea.l RT_HUNKS(a0),a1
 cmpi.w #$4eb9,$561c(a1)
 bne .bad
 lea $563a(a1),a3
 cmpa.l $561e(a1),a3
 bne .bad
 cmpi.w #$4eb9,$5622(a1)
 bne .bad
 movea.l a1,a3
 adda.l #$868c,a3
 cmpa.l $5624(a1),a3
 bne .bad
 ; Blitter ownership wrappers are shared by flight and its modal handoffs.
 ; Preserve the native OwnBlitter/WaitBlit/DisownBlitter ordering.
 cmpi.w #$2c79,-16(a3)
 bne .bad
 cmpi.l #$4eaefe38,-10(a3)
 bne .bad
 cmpi.l #$4eaeff1c,-6(a3)
 bne .bad
 cmpi.w #$4e75,-2(a3)
 bne .bad
 cmpi.w #$2c79,0(a3)
 bne .bad
 move.l -14(a3),d0
 cmp.l 2(a3),d0
 bne .bad
 cmpi.l #$4eaefe32,6(a3)
 bne .bad
 cmpi.w #$4e75,10(a3)
 bne .bad
 lea .patches(pc),a0
 jsr resload_Patch(a2)
.disabled:
 moveq #0,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,a0-a3
 rts
.patches:
 PL_START
 PL_PS $561c,timing_flight_entry
 PL_P $8686,timing_blitter_owned
 PL_P $8692,timing_blitter_release
 PL_END

; The initialized native flight owns its usual return to +05622. A failed
; enhanced transaction is never permission to resume the old world loop.
timing_flight_entry:
 movem.l d0-d7/a0-a6,-(sp)
 movea.l timing_runtime_arena(pc),a0
 lea timing_flight_exclude(pc),a1
 lea timing_flight_include(pc),a2
.call_base:
 lea .call_base(pc),a3
 adda.l #timing_runtime_loop-.call_base,a3
 jsr (a3)
 lea timing_flight_status(pc),a0
 move.l d0,(a0)
 cmpi.l #4,d0
 bne .failed
 movem.l (sp)+,d0-d7/a0-a6
 rts
.failed:
 ; WHDLoad restores the host environment. Keep exact loop failure in the
 ; diagnostic status word; do not discard its pending phase or replay effects.
 pea .message(pc)
 pea TDREASON_FAILMSG
 movea.l _resload(pc),a2
 jmp resload_Abort(a2)
.message:
 dc.b "Enhanced framerate: flight timing failed",0
 even

; Exec owns nesting/privilege transitions. Preserve ALL registers, especially
; D0's lifecycle result across Enable. No drawing/UI runs under exclusion.
timing_flight_exclude:
 movem.l d0-d7/a0-a6,-(sp)
 movea.l 4.w,a6
 jsr _LVODisable(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
timing_flight_include:
 movem.l d0-d7/a0-a6,-(sp)
 movea.l 4.w,a6
 jsr _LVOEnable(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
 even
timing_flight_status: dc.l 0

; A6 is graphics.library, already loaded by the native wrapper. OwnBlitter
; has completed; wait for its last DMA before masking only BLIT. Other
; interrupt sources retain their state. No queued blits are used by Gunship.
timing_blitter_owned:
 jsr -228(a6) ; WaitBlit
 movem.l d0/a0,-(sp)
 move.w $dff01c,d0 ; INTENAR
 andi.w #$0040,d0
 lea timing_blitter_intena(pc),a0
 move.w d0,(a0)
 move.w #$0040,$dff09a ; clear BLIT only
 movem.l (sp)+,d0/a0
 rts

; Restore the incoming BLIT enable before graphics.library releases ownership
; or services any queue. Leave a pending completion request for its handler.
timing_blitter_release:
 bsr timing_display_drain
 move.l d0,-(sp)
 move.w timing_blitter_intena(pc),d0
 beq .disabled
 ori.w #$8000,d0
 move.w d0,$dff09a
.disabled:
 move.l (sp)+,d0
 jmp -462(a6) ; DisownBlitter returns directly to the native caller
 even
timing_blitter_intena: dc.w 0
