; Phase 2 diagnostic seam. Included only by a VERIFY build, after the original.
; CUSTOM1=2 selects an English-only verification marker; CUSTOM1=0/1 preserves
; the original language choices. It installs no new game patches.
; Preserve all live outputs of resload_PatchSeg, including CCR.
verify_patchseg:
        jsr     116(a2)
        movem.l d0/a0,-(sp)
        move.w  ccr,-(sp)
        move.l  slave+$1de4(pc),d0
        cmpi.l  #2,d0
        bne.s   .off
        lea     verify_marker(pc),a0
        move.l  #1,(a0)
.off:
        move.w  (sp)+,ccr
        movem.l (sp)+,d0/a0
        rts
verify_marker:
        dc.l    0
        cnop    0,4
