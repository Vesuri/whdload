; Public OCS selection, after Psygore's PatchSeg and before any enhancement.
; install saves all registers. Original SetCPU and patch lists stay untouched.
ocs_option_gate:
        lea     ocs_option_tags(pc),a0
        jsr     $34(a2)                 ; resload_Control, CUSTOM5_GET
        ; CUSTOM5 bit 0 enables the enhanced framerate; bits 1-3 select the
        ; world speed: 0 Original, 1-4 a 10/12/15/20 Hz world (Original with
        ; the framerate is 1.0x with it); bits 4-6 the
        ; mouse (mouse_option), taken out first and kept for word_fixes.
        move.l  ocs_option_value(pc),d0
        moveq   #$70,d1
        and.l   d0,d1
        eor.l   d1,d0
        cmpi.l  #1,d0
        bne.s   .fixed
        moveq   #3,d0                   ; Enhanced framerate with Original speed: 1.0x
.fixed:
        lsr.w   #4,d1
        lea     ocs_option_value(pc),a0
        move.l  d0,(a0)
        lea     ocs_option_mouse(pc),a0
        move.w  d1,(a0)
        cmpi.l  #9,d0
        bhi.w   .off
        lsr.l   #1,d0
        beq.w   .off
        movea.l 4.w,a6
        move.w  296(a6),d0              ; Exec AttnFlags
        andi.w  #$008e,d0               ; 020/030/040/060, not 68010
        beq.w   .off
        ; KickEmu excludes the slave reservation from Exec's allocations, so
        ; TypeOfMem(slave) cannot certify its bank. Inspect the actual Exec
        ; memory headers instead. MEMF_FAST alone also labels trapdoor RAM.
        movea.l 322(a6),a0              ; Exec MemList.lh_Head
.next:
        tst.l   (a0)                   ; tail sentinel has no successor
        beq.s   .off
        move.w  14(a0),d0              ; mh_Attributes
        andi.w  #6,d0                   ; FAST, not CHIP
        cmpi.w  #4,d0
        bne.s   .skip
        move.l  20(a0),d0              ; mh_Lower
        move.l  24(a0),d1              ; mh_Upper (exclusive)
        cmp.l   d0,d1
        bls.s   .skip
        cmpi.l  #$200000,d0
        bcs.s   .skip
        cmpi.l  #$1000000,d0            ; true high Fast bank
        bcc.s   .on
        cmpi.l  #$a00000,d1             ; audited Zorro II bank
        bhi.s   .skip                  ; excludes slow/ROM/custom space
.on:
        move.l  ocs_option_value(pc),d0
        lea     .on(pc),a0
        adda.l  #timing_high_framerate-.on,a0
        move.w  d0,(a0)
        andi.w  #1,(a0)
        lsr.l   #1,d0
        move.b  .rates-1(pc,d0.w),d0
        ext.w   d0
        ext.l   d0
        lea     .on(pc),a0
        adda.l  #timing_flight_rate-.on,a0
        move.l  d0,(a0)
        moveq   #1,d0
        rts
.rates: dc.b    10,12,15,20
.skip:
        movea.l (a0),a0
        bra.s   .next
.off:
        moveq   #0,d0
        rts
ocs_option_tags:
        dc.l    $8800000b
ocs_option_value:
        dc.l    0                      ; absent/zero means original
        dc.l    0
ocs_option_mouse:
        dc.w    0                      ; CUSTOM5 bits 4-6
