; VERIFY-only full wall-ray pass twin at legacy headings. Actor/world updates
; preceding h12:2808 execute only once. That pass clears the chunky view itself;
; map/texture inputs are read-only and its ray/object output cursors reset.
; Reuse the C2P staging buffer between conversions. W6's nested twin must be off.
_turn_pixels_install
        move.l (_custom5,pc),d0
        and.l #$280000,d0
        beq .done
        move.l (_custom5,pc),d0
        btst #7,d0
        bne .bad                    ; W6 twin shares the scratch allocation
        move.l (_h12,pc),a0
        cmp.l #$611423ca,(h12_027f2,a0)
        bne .bad
        lea (h12_00026,a0),a1
        cmp.l (h12_027f6,a0),a1
        bne .bad
        lea (_turn_ray_original+2,pc),a1
        lea (h12_02808,a0),a2
        move.l a2,(a1)
        ; PERF_RANGE h12:027f2 8 bit=7
        move.w #$4eb9,(h12_027f2,a0)
        lea (_turn_pixels,pc),a1
        move.l a1,(h12_027f4,a0)
        move.w #$4e71,(h12_027f8,a0)
.done   rts
.bad    lea (_turn_pixels_bad,pc),a0
        bra _c2p_abort

_turn_pixels
        bsr _turn_sweep_rays
        movem.l d0-a6,-(sp)
        move.l (_turn_active,pc),d0
        beq .single
        move.l (_h11,pc),a0
        moveq #0,d0
        ; Address heading through an explicit base to avoid 16-bit overflow.
        adda.l #$8000,a0
        move.w (h11_08c22-$8000,a0),d0
        divu.w #5,d0
        swap d0
        tst.w d0
        bne .single
        movem.l (sp),d0-a6
        bsr _turn_ray_original
        movem.l d0-a6,-(sp)
        move.l (_h11,pc),a0
        move.l (h11_05fc2,a0),a0
        lea (_c2p_function,pc),a1
        adda.l #_c2p_chunky-_c2p_function,a1
        move.w #4999,d0
.copy   move.l (a0)+,(a1)+
        dbf d0,.copy
        lea (_turn_active,pc),a0
        clr.l (a0)
        move.l (_h12,pc),a0
        move.w #5,(h12_00038,a0)
        movem.l (60,sp),d0-a6
        bsr _turn_ray_original
        move.l (_h11,pc),a0
        move.l (h11_05fc2,a0),a0
        lea (_c2p_function,pc),a1
        adda.l #_c2p_chunky-_c2p_function,a1
        move.w #4999,d0
.compare
        cmpm.l (a0)+,(a1)+
        bne .different
        dbf d0,.compare
        lea (_turn_active,pc),a0
        move.l (_turn_owned,pc),(a0)
        move.l (_h12,pc),a0
        move.w #1,(h12_00038,a0)
        lea (_turn_pixel_counts,pc),a1
        move.w (h12_0002e,a0),d0
        cmp.w #80,d0
        beq .count
        addq.l #4,a1
        cmp.w #112,d0
        beq .count
        addq.l #4,a1
.count  addq.l #1,(a1)
        movem.l (sp)+,d0-a6
        lea (60,sp),sp
        bra .publish
.single movem.l (sp)+,d0-a6
        bsr _turn_ray_original
.publish
        move.l a0,-(sp)
        move.l (_h12,pc),a0
        move.l a2,(h12_00026,a0)
        move.l (sp)+,a0
        rts
.different
        lea (_turn_pixels_bad,pc),a0
        bra _c2p_abort
_turn_ray_original dc.w $4ef9
        dc.l 0
_turn_pixel_counts dc.l 0,0,0
_turn_pixels_bad dc.b "1 degree turning: wall pixel twin mismatch/configuration",0
        EVEN

        INCLUDE turning_sweep.s
