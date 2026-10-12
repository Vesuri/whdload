; Transactional native-hunk patch ownership for overlay unload/reload.
; A0 = zeroed 24-byte context; A1 = live native BPTR table for Begin.
; Caller excludes native execution/interrupts from Begin through Seal and during
; Restore, then flushes the instruction cache before permitting execution again.
; Begin snapshots live hunk payloads; Seal retains only changed words. Repeated
; transactions append, and Restore unwinds them in reverse order before free.
; Native game state must not advance between Begin and Seal.
; D0=0 success / -1 failure; all other registers preserved. Default-off/68000.
 ifnd FF1_PUBLIC_PATCHES
FF1_PUBLIC_PATCHES equ 0
 endc
 ifne FF1_PUBLIC_PATCHES
 ifnd FF1_PATCH_HUNKS
FF1_PATCH_HUNKS equ 206
 endc
 ifnd FF1_PATCH_LEDGER_BYTES
FF1_PATCH_LEDGER_BYTES equ 16384
 endc
FF1PatchBegin:
 movem.l d1-d7/a0-a6,-(sp)
 move.l a0,a5
 tst.l (a5)
 bne.w .bad
 move.l a1,20(a5)
 move.l a1,a2
 moveq #4,d3
 move.w #FF1_PATCH_HUNKS-1,d7
.size:
 move.l (a2)+,d0
 beq.w .bad
 lsl.l #2,d0
 move.l d0,a3
 move.l -4(a3),d0
 cmpi.l #8,d0
 blo.w .bad
 cmpi.l #$100000,d0
 bhi.w .bad
 move.l d0,d1
 andi.w #3,d1
 bne.w .bad
 add.l d0,d3
 bcs.w .bad
 dbra d7,.size
 move.l d3,d0
 bsr.w FF1PublicAcquire
 tst.l d0
 beq.w .bad
 tst.l 8(a5)
 bne.b .snapshot
 lea 8(a5),a0
 move.l #FF1_PATCH_LEDGER_BYTES,d0
 bsr.w FF1PublicAcquire
 tst.l d0
 beq.w .release_bad
 clr.l 16(a5)
.snapshot:
 move.l 20(a5),a2
 move.l (a5),a3
 move.w #FF1_PATCH_HUNKS-1,d7
.hunk:
 move.l (a2)+,d0
 lsl.l #2,d0
 move.l d0,a4
 move.l -4(a4),d6
 subq.l #8,d6
 addq.l #4,a4
 move.l a4,(a3)+
 move.l d6,(a3)+
 bra.b .test
.copy:
 move.l (a4)+,(a3)+
 subq.l #4,d6
.test:
 tst.l d6
 bne.b .copy
 dbra d7,.hunk
 clr.l (a3)
 moveq #0,d0
 bra.b .done
.release_bad:
 move.l a5,a0
 bsr.w FF1PublicRelease
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d7/a0-a6
 rts

FF1PatchSeal:
 movem.l d1-d7/a0-a6,-(sp)
 move.l a0,a5
 move.l (a5),d0
 beq.w .bad
 move.l d0,a3
 move.l 8(a5),a2
 adda.l 16(a5),a2
 move.l 12(a5),d7
 sub.l 16(a5),d7
.hunk:
 move.l (a3)+,d0
 beq.b .success
 move.l d0,a4
 move.l (a3)+,d6
 bra.b .test
.word:
 move.w (a3)+,d0
 cmp.w (a4),d0
 beq.b .next
 cmpi.l #6,d7
 blo.b .rollback
 move.l a4,(a2)+
 move.w d0,(a2)+
 subq.l #6,d7
.next:
 addq.l #2,a4
 subq.l #2,d6
.test:
 tst.l d6
 bne.b .word
 bra.b .hunk
.success:
 move.l a2,d0
 sub.l 8(a5),d0
 move.l d0,16(a5)
 move.l a5,a0
 bsr.w FF1PublicRelease
 moveq #0,d0
 bra.b .done
.rollback:
 ; Capacity failure rolls back this complete transaction, including changes
 ; not yet visited. Earlier sealed transactions remain owned by the ledger.
 move.l (a5),a3
.restore_hunk:
 move.l (a3)+,d0
 beq.b .release_bad
 move.l d0,a4
 move.l (a3)+,d6
 bra.b .restore_test
.restore_word:
 move.l (a3)+,(a4)+
 subq.l #4,d6
.restore_test:
 tst.l d6
 bne.b .restore_word
 bra.b .restore_hunk
.release_bad:
 move.l a5,a0
 bsr.w FF1PublicRelease
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d7/a0-a6
 rts

FF1PatchRestore:
 movem.l d1-d7/a0-a6,-(sp)
 move.l a0,a5
 move.l 8(a5),a2
 move.l 16(a5),d6
 adda.l d6,a2
 bra.b .test
.word:
 subq.l #6,a2
 move.l (a2),a3
 move.w 4(a2),(a3)
 subq.l #6,d6
.test:
 tst.l d6
 bne.b .word
 clr.l 16(a5)
 clr.l 20(a5)
 bsr.w FF1PublicRelease
 lea 8(a5),a0
 bsr.w FF1PublicRelease
 moveq #0,d0
 movem.l (sp)+,d1-d7/a0-a6
 rts
 endc
