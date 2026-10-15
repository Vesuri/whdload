; SPS 0481 public-memory lifecycle for the elapsed-time candidate.
; Default-off. 68020 fine path only; invoke after WHDLoad profile selection and
; explicit hunk binding. No release slave calls this module by default.
; The host supplies public_table/bound/control, public_reset_ranges, selection
; state, start, and the B6 probe symbols. Reset entries are explicit zero-data
; spans (offset.l,size.l), terminated by -1; code/binding metadata are excluded.
; Begin/Seal enclose hook writes. The native loop-exit boundary restores hooks
; before cleanup; the native unload hook also restores before FreeMem. Resident
; loader code and the private context remain owned for the entire invocation.
 ifnd FF1_PUBLIC_LIFECYCLE
FF1_PUBLIC_LIFECYCLE equ 0
 endc
 ifne FF1_PUBLIC_LIFECYCLE
public_install_boundary:
 tst.w public_control(pc)
 bne.b .control_done
 cmpi.l #$30390006,$65174
 bne.b .bad
 cmpi.w #$6be0,$65178
 bne.b .bad
 move.w #$4ef9,$65174
 lea (public_loop_entry.l,pc),a0
 move.l a0,$65176
.control_done:
 rts
.bad:
 bsr.w public_seal
 move.l $4.w,a6
 jsr -120(a6)
 bsr.w public_rollback
 move.l $4.w,a6
 jsr -126(a6)
 rts
public_loop_entry:
 move.w $66be0,d0
 move.w ccr,-(sp)
 cmpi.w #1,d0
 bne.b .done
 movem.l d0-d7/a0-a6,-(sp)
 move.l $4.w,a6
 jsr -120(a6)
 lea (public_patch_context.l,pc),a0
 bsr.l FF1PatchRestore
 bsr.w public_reset
 bsr.w public_flush
 IFND FF1_PRODUCTION
 lea (public_race_returns.l,pc),a0
 addq.l #1,(a0)
 ENDC
 move.l $4.w,a6
 jsr -126(a6)
 movem.l (sp)+,d0-d7/a0-a6
.done:
 move.w (sp)+,ccr
 jmp $6517a
public_race_returns: dc.l 0
; B7 integration-only lifecycle glue. Called with original loader registers.
public_begin_early:
 tst.l installed(pc)
 bne.b public_nothing
 bsr.w public_begin
public_nothing:
 rts
public_begin:
 movem.l d0-d7/a0-a6,-(sp)
 move.l $4.w,a6
 jsr -120(a6)
 lea (public_patch_context.l,pc),a0
 move.l public_table(pc),a1
 bsr.l FF1PatchBegin
 tst.l d0
 bne.b .bad
 lea (public_transaction.l,pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 bsr.w public_rollback
 move.l $4.w,a6
 jsr -126(a6)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
public_seal:
 tst.l public_transaction(pc)
 beq.b public_nothing
 movem.l d0-d7/a0-a6,-(sp)
 lea (public_transaction.l,pc),a0
 clr.l (a0)
 lea (public_patch_context.l,pc),a0
 bsr.l FF1PatchSeal
 tst.l d0
 beq.b .flush
 bsr.w public_rollback
.flush:
 bsr.w public_flush
 move.l $4.w,a6
 jsr -126(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
public_flush:
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 IFD FF1_PRODUCTION
 move.l FF1_HOST_RESLOAD(a2),a2
 ELSE
 move.l $1180(a2),a2
 ENDC
 jsr $20(a2)
 rts
public_rollback:
 lea (public_patch_context.l,pc),a0
 bsr.l FF1PatchRestore
 bsr.w public_reset
 IFD FF1_PRODUCTION
 bra.l FF1ProductionFault
 ENDC
 lea (selection_path.l,pc),a0
 move.l #1,(a0)
 move.l #100,4(a0)
 IFND FF1_PRODUCTION
 lea (public_fallbacks.l,pc),a0
 addq.l #1,(a0)
 ENDC
 bsr.w public_flush
 rts
public_install_lifetime:
 movem.l d0-d7/a0-a6,-(sp)
 tst.w public_control(pc)
 bne.b .done
 tst.l public_unload_installed(pc)
 bne.b .done
 move.l public_table(pc),a0
 move.l (a0),d0
 lsl.l #2,d0
 addi.l #4+$35c,d0
 move.l d0,a0
 cmpi.l #$48e7e00e,(a0)
 bne.b .bad
 cmpi.l #$202c0004,4(a0)
 bne.b .bad
 move.w #$4ef9,(a0)
 lea public_unload(pc),a1
 move.l a1,2(a0)
 move.w #$4e71,6(a0)
 addq.l #8,d0
 lea public_unload_jump+2(pc),a1
 move.l d0,(a1)
 lea (public_unload_installed.l,pc),a0
 move.l #1,(a0)
 bsr.w public_flush
 bra.b .done
.bad:
 lea (selection_path.l,pc),a0
 move.l #1,(a0)
 move.l #100,4(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
public_unload:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 cmpi.l #$22f30,(a4)
 bne.b .done
 move.l $4.w,a6
 jsr -120(a6)
 lea (public_patch_context.l,pc),a0
 bsr.l FF1PatchRestore
 bsr.w public_reset
 bsr.w public_flush
 IFND FF1_PRODUCTION
 lea (public_unloads.l,pc),a0
 addq.l #1,(a0)
 ENDC
 move.l $4.w,a6
 jsr -126(a6)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 movem.l d0-d2/a4-a6,-(sp)
 move.l 4(a4),d0
public_unload_jump:
 jmp $0.l
public_reset:
 IFD FF1_FINE_BLIT_OWNER
 bsr.l FF1FineBlitRestore
 ENDC
 lea (public_reset_ranges.l,pc),a0
 lea start(pc),a2
.range:
 move.l (a0)+,d0
 bmi.b .done
 move.l (a0)+,d1
 move.l a2,a1
 adda.l d0,a1
.byte:
 clr.b (a1)+
 subq.l #1,d1
 bne.b .byte
 bra.b .range
.done:
 lea (public_bound.l,pc),a0
 clr.l (a0)
 rts
public_transaction: dc.l 0
public_unload_installed: dc.l 0
public_unloads: dc.l 0
public_fallbacks: dc.l 0
public_patch_context: ds.l 6
 include "FerrariFormulaOne_PublicPatches.s"
 endc
