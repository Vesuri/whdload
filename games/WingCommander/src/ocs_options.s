; Public OCS selection, after Psygore's PatchSeg and before any enhancement.
; install saves all registers. Original SetCPU and patch lists stay untouched.
ocs_option_gate:
        lea     ocs_option_tags(pc),a0
        jsr     $34(a2)                 ; resload_Control, CUSTOM5_GET
        lea     ocs_option_value(pc),a0
        cmpi.l  #1,(a0)
        bne.s   .off
        movea.l 4.w,a6
        move.w  296(a6),d0              ; Exec AttnFlags
        andi.w  #$008e,d0               ; 020/030/040/060, not 68010
        beq.s   .off
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
        moveq   #1,d0
        rts
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
