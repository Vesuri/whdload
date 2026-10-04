; Runtime twin, VERIFY + CUSTOM5 bit 3. No original game bytes in this source.
; Copy the original shape routine BEFORE PatchSeg and relocate its only external
; PC-relative call through a local absolute jump. Replay identical inputs and
; initial destination pixels; compare all bitmap planes and clipping carry.
; This deliberately serialises both twins: speed measurements use bit 3 OFF.
verify_draw_init:
    movem.l d0-a6,-(sp)
    move.l sim_drive_enabled(pc),d0
    btst #3,d0
    beq .done
    move.l render_options(pc),d0
    btst #1,d0
    beq .done
    lea verify_draw_vars(pc),a3
    move.l d7,d0
    lsl.l #2,d0
    addq.l #4,d0
    move.l d0,12(a3)          ; root code address
    move.l #131492,d0        ; 420 bytes code + two 64K pixel shadows
    move.l #$10001,d1
    move.l $4.w,a6
    jsr -198(a6)
    move.l d0,(a3)
    beq .failed
    move.l d0,a1
    move.l 12(a3),a0
    adda.l #$f114,a0
    moveq #102,d0
.copy
    move.l (a0)+,(a1)+
    dbf d0,.copy
    move.w #$4ef9,(a1)+       ; jmp abs.l (original clipping routine)
    move.l 12(a3),d0
    add.l #$efc6,d0
    move.l d0,(a1)
    move.l (a3),a1
    move.w #404,8(a1)        ; displacement from copied JSR's extension word
    lea 420(a1),a0
    move.l a0,4(a3)
    adda.l #65536,a0
    move.l a0,8(a3)
    move.l _resload(pc),a2
    jsr resload_FlushCache(a2)
    bra .done
.failed
    lea verify_draw_results(pc),a0
    addq.l #1,(a0)
.done
    movem.l (sp)+,d0-a6
    rts

verify_draw_shape:
    movem.l d0-a6,-(sp)
    lea verify_draw_vars(pc),a0
    move.l sp,16(a0)
    tst.l (a0)
    beq .skip
    move.l sim_epoch(pc),d0
    beq .skip               ; verify racing, without slowing the intro
    bsr render_wait_owned
    move.l -12852(a4),a1
    move.l a1,20(a0)
    moveq #0,d0
    move.w (a1),d0
    mulu.w 2(a1),d0
    lea verify_draw_vars(pc),a0
    move.l d0,24(a0)         ; bytes per plane
    move.l d0,d2
    and.w #3,d2
    bne .invalid            ; these game bitmaps have long-sized planes
    moveq #0,d1
    move.b 5(a1),d1
    mulu.w d1,d0
    cmp.l #65536,d0
    bhi .invalid
    tst.l d0
    beq .invalid
    moveq #0,d0              ; save initial pixels
    bsr verify_draw_pixels
    bsr verify_draw_irq_on
    movem.l (sp),d0-a6
    bsr verify_draw_original
    scs -(sp)
    bsr render_wait_owned
    move.b (sp)+,d0
    lea verify_draw_vars(pc),a0
    move.b d0,28(a0)
    move.w #$40,$dff09a      ; patched twin: same code, unused IRQ disabled
    moveq #1,d0              ; save original's result
    bsr verify_draw_pixels
    moveq #2,d0              ; restore initial pixels
    bsr verify_draw_pixels
    movem.l (sp),d0-a6
    bsr verify_draw_updated
    scs -(sp)
    movem.l d0-a6,-(sp)      ; return the updated routine's registers intact
    bsr render_wait_owned
    moveq #3,d0
    bsr verify_draw_pixels
    lea verify_draw_results(pc),a0
    addq.l #1,4(a0)
    lea verify_draw_vars(pc),a1
    move.b 60(sp),d0
    cmp.b 28(a1),d0
    beq.b .carry_ok
    addq.l #1,(a0)
.carry_ok
    tst.b 60(sp)
    beq.b .clear_carry
    movem.l (sp)+,d0-a6
    addq.l #2,sp
    adda.l #60,sp            ; discard input register frame
    ori.b #1,ccr
    rts
.clear_carry
    movem.l (sp)+,d0-a6
    addq.l #2,sp
    adda.l #60,sp
    andi.b #$fe,ccr
    rts
.invalid
    lea verify_draw_results(pc),a0
    addq.l #1,(a0)
.skip
    movem.l (sp)+,d0-a6
    bra verify_draw_updated

verify_draw_irq_on:
    move.l a0,-(sp)
    lea render_saved_irq(pc),a0
    tst.w (a0)
    beq.b .done
    move.w #$8040,$dff09a
.done
    move.l (sp)+,a0
    rts
; Verification only: wait before CPU snapshots and after each completed twin.
render_wait_owned:
    move.l a6,-(sp)
    lea $dff000,a6
    btst #6,2(a6)
.loop
    btst #6,2(a6)
    bne.b .loop
    move.l (sp)+,a6
    rts

verify_draw_original:
    move.l verify_draw_vars(pc),-(sp)
    rts
verify_draw_updated:
    IFD CPUSHAPES
    move.l a0,-(sp)
    lea render_cpu_enabled(pc),a0
    tst.w (a0)
    movem.l (sp)+,a0
    bne render_cpu_shape        ; CUSTOM2 bit 3 on 68020+: twin the CPU drawer
    ENDC
    movem.l d0-d6/a0-a3/a5,-(sp)
    move.l a0,a5
    move.l -32266(a4),-(sp)
    add.l #$f11a-$e9e2,(sp)
    rts

; d0=0 snapshot / 1 expected / 2 restore / 3 compare. Bitmap may have
; discontiguous planes; flatten only the shadows, never the actual allocation.
verify_draw_pixels:
    lea verify_draw_vars(pc),a0
    move.l 4(a0),a2
    tst.w d0
    beq.b .buffer
    cmp.w #2,d0
    beq.b .buffer
    move.l 8(a0),a2
.buffer
    move.l 20(a0),a1
    moveq #0,d3
    move.b 5(a1),d3
    subq.w #1,d3
    addq.l #8,a1
    moveq #0,d4              ; flattened byte offset
.plane
    move.l (a1)+,a3
    move.l 24(a0),d2
    lsr.l #2,d2
    subq.w #1,d2
    cmp.w #2,d0
    beq.b .restore
    cmp.w #3,d0
    beq.b .compare
.copy
    move.l (a3)+,(a2)+
    addq.l #4,d4
    dbf d2,.copy
    bra.b .next_plane
.restore
    move.l (a2)+,(a3)+
    addq.l #4,d4
    dbf d2,.restore
    bra.b .next_plane
.compare
    move.l (a3)+,d1
    cmp.l (a2)+,d1
    beq.b .next
    lea verify_draw_results(pc),a5
    addq.l #1,(a5)
    tst.l 8(a5)
    bne.b .next
    move.l d4,8(a5)
    addq.l #1,8(a5)          ; first mismatched long's byte offset +1
.next
    addq.l #4,d4
    dbf d2,.compare
.next_plane
    dbf d3,.plane
    rts

verify_draw_vars:
    dc.l 0,0,0,0,0,0,0
    dc.w 0
    dc.b "TD2DRAWCHK",0
    even
verify_draw_results:
    dc.l 0,0,0              ; mismatch count, shape calls, first long byte offset+1
