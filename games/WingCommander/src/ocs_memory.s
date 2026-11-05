; P13C4 source allocation transaction; task context, base 68000 ISA.
; O:31e1e hook replaces push D0 / jsr (A0) / discard argument (6 bytes).
; D0=size, A0=native allocator, A2=surface; native D2-D7/A2-A6 ABI.
; Only the primary source (A4+$10e2) is eligible. Native registry owns both
; Fast and Chip allocations, so normal surface and overall cleanup remain valid.
; OCS_* entry equates are supplied by the installer, never inferred by CPU type.
ocs_source_allocate:
        cmpa.l  #OCS_CHIP_ALLOC,a0
        bne.w   .native
        lea     $10e2(a4),a1
        cmpa.l  a1,a2
        bne.w   .native
        lea     ocs_source_backend(pc),a1
        clr.l   (a1)
        move.l  ocs_requested_backend(pc),d1
        beq.w   .native
        cmpi.w  #320,20(a2)
        bne.w   .native
        cmpi.w  #200,22(a2)
        bne.w   .native
        movem.l d2-d7/a2-a6,-(sp)
        move.l  d0,d7
        movea.l a0,a5
        movea.l 4.w,a6
        move.l  #$10005,d1       ; CLEAR | FAST | PUBLIC
        jsr     -198(a6)
        tst.l   d0
        beq.s   .fallback
        ; Admit only the audited Zorro II Fast bank. In particular, reject
        ; trapdoor RAM even though Exec also labels that memory MEMF_FAST.
        cmpi.l  #$200000,d0
        bcs.s   .reject
        move.l  d0,d1
        add.l   d7,d1
        bcs.s   .reject
        cmpi.l  #$a00000,d1
        bhi.s   .reject
        move.l  d7,d1
        jsr     OCS_REGISTER    ; native registry frees block if full
        tst.l   d0
        beq.s   .fallback
        lea     ocs_source_backend(pc),a1
        move.l  ocs_requested_backend(pc),(a1)
        movem.l (sp)+,d2-d7/a2-a6
        rts
.reject:
        movea.l d0,a1
        move.l  d7,d0
        movea.l 4.w,a6
        jsr     -210(a6)
.fallback:
        move.l  d7,d0
        movea.l a5,a0
        movem.l (sp)+,d2-d7/a2-a6
.native:
        move.l  d0,-(sp)
        jsr     (a0)
        addq.l  #4,sp
        rts

; C ABI: surface, rectangle. Called instead of O:31dc4 at the main-source
; constructor O:c94, before view aliases or compositor commands are built.
; A zero result rolls back the native partial source/row-table transaction.
; The installation must turn failure into a controlled out-of-memory exit;
; the original caller ignores D0 and must not proceed to O:32554 on failure.
ocs_source_create:
        movem.l d2-d7/a2-a6,-(sp)
        movea.l 48(sp),a2
        move.l  52(sp),-(sp)
        move.l  a2,-(sp)
        jsr     OCS_SURFACE_CREATE
        addq.l  #8,sp
        tst.l   d0
        bne.s   .done
        move.l  a2,-(sp)
        jsr     OCS_SURFACE_FREE
        addq.l  #4,sp
        lea     ocs_source_backend(pc),a0
        clr.l   (a0)
        moveq   #0,d0
.done:
        movem.l (sp)+,d2-d7/a2-a6
        rts

ocs_requested_backend: dc.l 0
ocs_source_backend: dc.l 0

; Replace O:324c0. Unlike the native constructor, check the plane allocation
; before constructing conversion descriptors and unwind either partial failure.
; The caller must have closed the preceding display before requesting a new one.
ocs_display_create:
        movem.l d2/a2,-(sp)
        move.w  14(sp),-(sp)
        move.w  14(sp),-(sp)
        jsr     OCS_DISPLAY_CREATE
        addq.l  #4,sp
        tst.l   d0
        beq.s   .failed
        lea     OCS_CONVERSION+16,a2
        moveq   #1,d2
.next:
        move.l  #668,-(sp)
        jsr     OCS_PUBLIC_ALLOC
        addq.l  #4,sp
        move.l  d0,(a2)+
        beq.s   .failed
        dbra    d2,.next
        moveq   #1,d0
        bra.s   .done
.failed:
        jsr     OCS_DISPLAY_FREE
        moveq   #0,d0
.done:
        movem.l (sp)+,d2/a2
        rts

; Replace O:32476. Retire the native queue before releasing the primary source,
; including source rollback; unrelated offscreen surfaces keep native semantics.
; Resume after the displaced A2 save/load so the original registry/free code
; clears the source and row owners exactly once.
ocs_source_free:
        movem.l d0-d7/a0-a6,-(sp)
        movea.l 64(sp),a2
        lea     $10e2(a4),a0
        cmpa.l  a0,a2
        bne.s   .resume
        jsr     OCS_WAIT
        lea     ocs_source_backend(pc),a0
        clr.l   (a0)
        lea     OCS_CONVERSION,a0
        clr.l   (a0)
        clr.l   8(a0)
.resume:
        movem.l (sp)+,d0-d7/a0-a6
        move.l  a2,-(sp)
        movea.l 8(sp),a2
        jmp     OCS_SURFACE_FREE_BODY
