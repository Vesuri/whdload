; VERIFY only: capture CCR directly on 68010+, avoiding privileged SR reads.
; On a 68000 leave the legal MOVE SR opcodes untouched. All comparisons already
; mask X/N/Z/V/C, and restoration uses CCR only; upper SR bits are never required.
_verify_ccr_install
        movem.l d0-d2/a0-a2,-(sp)
        move.l (_lov_attnflags,pc),d0
        btst #0,d0              ; AFB_68010, also set for later CPUs
        beq .done
        lea (_verify_ccr_offsets,pc),a1
        moveq #(_verify_ccr_end-_verify_ccr_offsets)/4-1,d2
.site   lea (_verify_ccr_offsets,pc),a0
        adda.l (a1)+,a0
        move.w (a0),d0
        and.w #$ffc0,d0
        cmp.w #$40c0,d0
        bne .bad
        ori.w #$0200,(a0)      ; MOVE SR -> MOVE CCR, identical effective address
        dbf d2,.site
        lea (_verify_ccr_patched,pc),a0
        move.w #(_verify_ccr_end-_verify_ccr_offsets)/4,(a0)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-d2/a0-a2
        rts
.bad    lea (_verify_ccr_badmsg,pc),a0
        bra _c2p_abort
_verify_ccr_badmsg dc.b "VERIFY: unexpected flag-capture opcode",0
        EVEN
_verify_ccr_patched dc.w 0
_verify_ccr_site_count dc.w (_verify_ccr_end-_verify_ccr_offsets)/4
        CNOP 0,4
_verify_ccr_offsets
; Include only features present in this revision, so each feature commit builds
; independently. Flag-site IDs remain stable as subsequent patches are added.
        IFD _verify_sr_0
        dc.l _verify_sr_0-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_1
        dc.l _verify_sr_1-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_2
        dc.l _verify_sr_2-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_3
        dc.l _verify_sr_3-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_4
        dc.l _verify_sr_4-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_5
        dc.l _verify_sr_5-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_6
        dc.l _verify_sr_6-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_7
        dc.l _verify_sr_7-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_8
        dc.l _verify_sr_8-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_9
        dc.l _verify_sr_9-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_10
        dc.l _verify_sr_10-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_11
        dc.l _verify_sr_11-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_12
        dc.l _verify_sr_12-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_13
        dc.l _verify_sr_13-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_14
        dc.l _verify_sr_14-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_15
        dc.l _verify_sr_15-_verify_ccr_offsets
        ENDC
        IFD _verify_sr_16
        dc.l _verify_sr_16-_verify_ccr_offsets
        ENDC
_verify_ccr_end
