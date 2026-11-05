; VERIFY-only bitmap/clear ceiling. Both arms execute the same installation path.
; Preserve every PatchSeg output and CCR; retain the original c2p and limiter.
drawing_patchseg:
        jsr     116(a2)
        movem.l d0-d7/a0-a6,-(sp)
        move.w  ccr,-(sp)
        tst.l   slave+$1de4(pc)
        bne.s   .wrong
        move.l  d7,d0
        lsl.l   #2,d0
        addq.l  #4,d0
        movea.l d0,a0
        ; Both functions begin with a register-save MOVEM in the pinned English build.
        cmpi.w  #$48e7,$2efe8(a0)
        bne.s   .wrong
        cmpi.w  #$48e7,$31cd6(a0)
        bne.s   .wrong
        move.w  drawing_patch_word(pc),d0
        move.w  d0,$2efe8(a0)
        move.w  drawing_patch_word+2(pc),d0
        move.w  d0,$31cd6(a0)
        lea     drawing_installs(pc),a0
        addq.l  #1,(a0)
        jsr     32(a2)                 ; resload_FlushCache
        move.w  (sp)+,ccr
        movem.l (sp)+,d0-d7/a0-a6
        rts
.wrong:
        move.l  #9,-(sp)               ; TDREASON_WRONGVER
        jmp     4(a2)
        cnop    0,4
drawing_installs:
        dc.l    0
drawing_patch_word:
        dc.w    BITMAP_OPCODE,CLEAR_OPCODE
