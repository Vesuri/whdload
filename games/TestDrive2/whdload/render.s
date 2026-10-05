; v1 CUSTOM2 bit 1: give the blitter bus priority (DMACON BLTPRI) and disable
; graphics.library's unused blitter-finished interrupt while the game runs.
; The CPU only polls BBUSY during shape blits, so its DMACONR reads no longer
; take the blitter's slots. Game code, waits and ownership are unchanged.
; Preserves the game entry's registers; restore puts back the original enables.
render_interrupt_option:
    movem.l d0/a0,-(sp)
    move.l render_options(pc),d0
    btst #1,d0
    beq.b .done
    lea render_saved_priority(pc),a0
    move.w $dff002,d0
    and.w #$400,d0
    move.w d0,(a0)+
    move.w $dff01c,d0
    and.w #$40,d0
    move.w d0,(a0)            ; render_saved_irq
    move.w #$8400,$dff096
    move.w #$40,$dff09a
.done
    movem.l (sp)+,d0/a0
    rts
render_interrupt_restore:
    move.l d0,-(sp)
    move.l render_options(pc),d0
    btst #1,d0
    beq.b .done
    move.w render_saved_priority(pc),d0
    bne.b .priority
    move.w #$0400,$dff096
.priority
    move.w render_saved_irq(pc),d0
    beq.b .done
    move.w #$8040,$dff09a
.done
    move.l (sp)+,d0
    rts
render_saved_priority: dc.w 0
render_saved_irq: dc.w 0

; v1 CUSTOM2 bit 2: project each view at the latched fractional road position.
; The bottom row and mirror horizon retain their original scales.
render_subunit_main:
    move.w #10,-7610(a4)
    movem.l d0-d6/a0-a3,-(sp)
    lea -26778(a4),a0
    lea -26868(a4),a1
    lea -26688(a4),a2
    lea -5632(a4),a3          ; main row 1, field 18
    moveq #42,d5
    moveq #-2,d6
    bra.b render_subunit_rows
render_subunit_mirror:
    move.w #20,-7610(a4)
    movem.l d0-d6/a0-a3,-(sp)
    lea -26966(a4),a0
    lea -27016(a4),a1
    lea -26916(a4),a2
    lea -5630(a4),a3          ; mirror row 1, field 20
    moveq #21,d5
    moveq #2,d6
render_subunit_rows:
    move.w -13392(a4),d4
    IFD VERIFY
    move.l sim_drive_enabled(pc),d0
    btst #3,d0
    beq.b .fraction
    moveq #0,d4
.fraction
    ENDC
    lsr.w #1,d4              ; unsigned Q15, safe for MULS
.row
    move.w (0,a0,d6.w),d0
    sub.w (a0),d0
    muls.w d4,d0
    add.l d0,d0
    swap d0
    add.w (a0)+,d0
    move.w d0,(a3)
    move.w (0,a1,d6.w),d0
    sub.w (a1),d0
    muls.w d4,d0
    add.l d0,d0
    swap d0
    add.w (a1)+,d0
    move.w d0,4(a3)
    move.w (0,a2,d6.w),d0
    sub.w (a2),d0
    muls.w d4,d0
    add.l d0,d0
    swap d0
    add.w (a2)+,d0
    move.w d0,8(a3)
    mulu.w #162,d0
    move.w d0,30(a3)
    adda.w #52,a3
    dbf d5,.row
    bsr render_subunit_seed
    movem.l (sp)+,d0-d6/a0-a3
    rts

; Integrate only the visible fraction of the first segment. The original row
; walker still handles every complete segment; these seeds are renderer-only.
render_subunit_seed:
    tst.w d4
    beq.b .done
    move.w -13394(a4),d0
    addq.w #1,d0
    move.l -13148(a4),a0
    move.b (0,a0,d0.w),d0
    and.w #127,d0
    lsl.w #2,d0
    move.l -13152(a4),a0
    adda.w d0,a0
    move.b 1(a0),d2
    ext.w d2
    add.w d2,d2
    move.b 2(a0),d3
    ext.w d3
    lea -26166(a4),a1
    move.w d2,d0
    bsr.b render_subunit_angle
    tst.w d6
    bmi.b .main
    add.w d0,-14936(a4)
    move.w d3,d0
    bsr.b render_subunit_angle
    sub.w d0,-14932(a4)
    move.w -14932(a4),d0
    bsr.b render_subunit_sine
    add.w d0,-14928(a4)
    move.w -14936(a4),d0
    bsr.b render_subunit_sine
    add.w d0,-14930(a4)
.done
    rts
.main
    sub.w d0,-14936(a4)
    move.w d3,d0
    bsr.b render_subunit_angle
    add.w d0,-14932(a4)
    move.w -14932(a4),d0
    sub.w d3,d0
    bsr.b render_subunit_sine
    sub.w d0,-14928(a4)
    move.w -14936(a4),d0
    add.w d2,d0
    bsr.b render_subunit_sine
    sub.w d0,-14930(a4)
    rts
; Round 8.8 angle fractions so f -> 1 reaches the next lookup exactly.
render_subunit_angle:
    muls.w d4,d0
    add.l d0,d0
    add.l #$8000,d0
    swap d0
    rts
render_subunit_sine:
    asr.w #8,d0              ; high byte, as in the original MOVE.B of a word
    add.w d0,d0
    move.w (0,a1,d0.w),d0
    muls.w d4,d0
    add.l d0,d0
    swap d0
    rts

; Frame snapshots: traffic origins share one fraction per direction.
render_subunit_latch:
    move.l -13318(a4),-13366(a4)
    movem.l d0/a0,-(sp)
    lea render_traffic_fractions(pc),a0
    move.w -13468(a4),(a0)+
    move.w -13464(a4),(a0)
    movem.l (sp)+,d0/a0
    rts

render_subunit_forward:
    add.w d2,d0
    move.w 12(a3),d1
    movem.l d2-d4/a1,-(sp)
    move.w render_traffic_fractions(pc),d4
    moveq #0,d3
    bra.b render_subunit_object
render_subunit_oncoming:
    add.w d1,d0
    move.w 12(a3),d1
    movem.l d2-d4/a1,-(sp)
    move.w render_traffic_fractions+2(pc),d4
    moveq #1,d3
render_subunit_object:
    bsr render_subunit_neighbour
    beq.b .done
    move.w (26,a1,d6.w),d2
    lsr.w #1,d2
    tst.w d3
    bne.b .oncoming
    cmp.w #25,2(a0)
    beq.b .centre
    neg.w d2
    add.w 4(a1),d2
    bra.b .x
.oncoming
    cmp.w #17,2(a0)
    beq.b .left_centre
    add.w 2(a1),d2
    bra.b .x
.left_centre
    neg.w d2
.centre
    add.w 10(a1),d2
.x
    bsr render_subunit_xy
.done
    movem.l (sp)+,d2-d4/a1
    rts
render_subunit_opponent:
    add.w d2,d0
    move.w 12(a3),d1
    movem.l d2-d4/a1,-(sp)
    move.w -13372(a4),d4
    move.w -13370(a4),d3
    bra.b render_subunit_car
render_subunit_police:
    add.w d2,d0
    move.w 12(a3),d1
    movem.l d2-d4/a1,-(sp)
    move.w -13364(a4),d4
    move.w -13362(a4),d3
render_subunit_car:
    bsr render_subunit_neighbour
    beq.b .done
    move.w d3,d2
    bpl.b .positive
    neg.w d2
.positive
    mulu.w (48,a1,d6.w),d2
    tst.w d3
    bpl.b .scaled
    neg.l d2
.scaled
    swap d2
    add.w 10(a1),d2
    bsr render_subunit_xy
.done
    movem.l (sp)+,d2-d4/a1
    rts
; Road rows already subtract the camera fraction. Add only the car fraction;
; subtracting the camera twice would create a sawtooth at constant separation.
render_subunit_neighbour:
    IFD VERIFY
    move.l sim_drive_enabled(pc),d2
    btst #3,d2
    bne.b .zero
    ENDC
    tst.w 46(a3)
    beq.b .bottom
    lsr.w #1,d4
    beq.b .done
    lea 52(a3),a1
    tst.w d6
    bne.b .mirror
    cmp.w #43,46(a3)         ; no row beyond the horizon
    beq.b .zero
    bra.b .ready
.mirror
    lea -52(a3),a1
.ready
    tst.w d4
.done
    rts
; The fixed bottom row has no camera displacement. Use the relative fraction
; there, extrapolating from row 1 for a car beyond the viewport's near edge.
.bottom
    moveq #0,d2
    move.w -13392(a4),d2
    and.l #$ffff,d4
    tst.w d6
    beq.b .relative
    exg d2,d4
.relative
    sub.l d2,d4
    asr.l #1,d4
    lea 52(a3),a1
    tst.w d4
    rts
.zero
    moveq #0,d4
    rts
; d0/d1 = matched x/y, d2 = neighbour x, d4 = Q15 weight (signed at row 0).
render_subunit_xy:
    sub.w d0,d2
    muls.w d4,d2
    add.l d2,d2
    swap d2
    add.w d2,d0
    move.w 12(a1),d2
    sub.w d1,d2
    muls.w d4,d2
    add.l d2,d2
    swap d2
    add.w d2,d1
    rts
render_traffic_fractions: dc.w 0,0

    IFD VERIFY
verify_render_units:
    move.l sim_drive_enabled(pc),-(sp)
    lea sim_drive_enabled(pc),a0
    clr.l (a0)
    lea -5702(a4),a3
    lea verify_render_cases(pc),a2
    moveq #8,d7
.case
    move.w (a2)+,d6
    move.w (a2)+,46(a3)
    move.w (a2)+,-13392(a4)
    move.w (a2)+,d4
    bsr render_subunit_neighbour
    move.w d4,d0
    ext.l d0
    move.w (a2)+,d1
    ext.l d1
    bsr verify_equal
    dbf d7,.case
    move.w #1,46(a3)
    moveq #0,d6
    move.w #$ffff,d4
    bsr render_subunit_neighbour
    move.l a1,d0
    sub.l a3,d0
    moveq #52,d1
    bsr verify_equal
    moveq #2,d6
    move.w #$ffff,d4
    bsr render_subunit_neighbour
    move.l a1,d0
    sub.l a3,d0
    moveq #-52,d1
    bsr verify_equal
    lea sim_drive_enabled(pc),a0
    move.l #8,(a0)
    move.w #$ffff,d4
    bsr render_subunit_neighbour
    move.l d4,d0
    moveq #0,d1
    bsr verify_equal
    move.l (sp)+,(a0)
    rts
    dc.b "TD2RENDERCHECK",0
    even
verify_render_cases:
    ; view, row, camera fraction, car fraction, signed Q15 weight
    dc.w 0,43,0,$8000,0
    dc.w 0,0,$4000,$4000,0
    dc.w 2,0,$4000,$4000,0
    dc.w 0,0,$8000,0,-16384
    dc.w 0,0,0,$ffff,32767
    dc.w 2,0,0,$ffff,-32768
    dc.w 2,0,$ffff,0,32767
    dc.w 0,1,0,$ffff,32767
    dc.w 2,1,0,$ffff,32767
    ENDC

    IFD VERIFY
; Give both identity arms the same scanline input, including unused fields
; that the original pass otherwise retains from an earlier view or frame.
render_zero_main:
    bsr render_zero_table
    move.l d0,-(sp)
    move.l render_options(pc),d0
    btst #2,d0
    movem.l (sp)+,d0
    bne render_subunit_main
    move.w #10,-7610(a4)
    rts
render_zero_mirror:
    bsr render_zero_table
    move.l d0,-(sp)
    move.l render_options(pc),d0
    btst #2,d0
    movem.l (sp)+,d0
    bne render_subunit_mirror
    move.w #20,-7610(a4)
    rts
render_zero_table:
    movem.l d0-d1/a0,-(sp)
    lea -7574(a4),a0
    moveq #0,d0
    move.w #467,d1           ; 117 lines; row records begin immediately after
.clear
    move.l d0,(a0)+
    dbf d1,.clear
    movem.l (sp)+,d0-d1/a0
    rts
    ENDC

    IFD VERIFY
; A straight segment still advances laterally when the camera is turned.
verify_render_seed:
    lea -13100(a4),a0
    clr.w (a0)
    move.l a0,-13148(a4)
    lea -13090(a4),a0
    clr.l (a0)
    move.l a0,-13152(a4)
    clr.w -13394(a4)
    clr.w -26166(a4)
    move.w #8,-26164(a4)
    move.w #-8,-26168(a4)
    moveq #1,d7
.view
    move.w #256,-14936(a4)
    moveq #-2,d6
    tst.w d7
    bne.b .main
    neg.w -14936(a4)
    moveq #2,d6
.main
    clr.w -14932(a4)
    move.w #83,-14928(a4)
    clr.w -14930(a4)
    move.w #16384,d4
    bsr render_subunit_seed
    move.w -14930(a4),d0
    ext.l d0
    moveq #-4,d1
    bsr verify_equal
    dbf d7,.view
    rts
    dc.b "TD2SEEDCHECK",0
    even
    ENDC
