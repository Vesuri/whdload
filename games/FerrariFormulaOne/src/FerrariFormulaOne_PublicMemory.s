; Default-off memory ownership for the Ferrari loader, 68000-safe.
; The host supplies a WHDLoad-owned reservation AFTER the Kickstart image.
; Never pass memory already registered with Exec. The reservation lives until
; WHDLoad tears down KickEmu; this module never frees it to a different allocator.
; CPU-only allocations use MEMF_PUBLIC. DMA allocations remain MEMF_CHIP.
 ifnd FF1_PUBLIC_MEMORY
FF1_PUBLIC_MEMORY equ 0
 endc
 ifne FF1_PUBLIC_MEMORY
FF1PM_BASE equ 0
FF1PM_SIZE equ 4
FF1PM_BYTES equ 8
FF1PO_PTR equ 0
FF1PO_SIZE equ 4
FF1PO_BYTES equ 8

; A0 = zero-initialized pool context, A1 = reservation, D0 = byte size.
; D1 = verified memory attributes (PUBLIC, plus FAST iff host-qualified).
; Returns D0=0 on registration/idempotent repeat, -1 on invalid input.
; D1-D7/A0-A6 preserved. Calls Exec AddMemList, task context only.
FF1PublicPoolOpen:
 movem.l d1-d3/a0-a3/a6,-(sp)
 move.l a0,a3
 move.l a1,d2
 move.l d2,d3
 or.l d0,d3
 andi.l #7,d3
 bne.w .bad
 tst.l d2
 beq.w .bad
 cmpi.l #256,d0
 blo.w .bad
 move.l d2,d3
 add.l d0,d3
 bcs.w .bad
 tst.l FF1PM_BASE(a3)
 beq.b .new
 cmp.l FF1PM_BASE(a3),d2
 bne.b .bad
 cmp.l FF1PM_SIZE(a3),d0
 bne.b .bad
 bra.b .ok
.new:
 move.l d2,FF1PM_BASE(a3)
 move.l d0,FF1PM_SIZE(a3)
 move.l a1,a0
 andi.l #$00000005,d1       ; PUBLIC/FAST metadata, never CHIP by inference
 ori.l #1,d1
 moveq #10,d2              ; prefer this public expansion pool
 lea .name(pc),a1
 move.l $4.w,a6
 jsr -618(a6)              ; AddMemList (Kickstart 1.3)
.ok:
 moveq #0,d0
 bra.b .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d3/a0-a3/a6
 rts
.name: dc.b 'Ferrari public memory',0
 even

; A0 = zero-initialized allocation owner, D0 = nonzero requested bytes.
; Returns D0=pointer or 0. Existing ownership is never overwritten.
; D1-D7/A0-A6 preserved. No forced Fast request or second allocation policy.
FF1PublicAcquire:
 movem.l d1-d2/a0-a2/a6,-(sp)
 move.l a0,a2
 tst.l FF1PO_PTR(a2)
 bne.b .bad
 tst.l d0
 beq.b .bad
 move.l d0,d2
 moveq #1,d1              ; MEMF_PUBLIC
 move.l $4.w,a6
 jsr -198(a6)             ; AllocMem
 tst.l d0
 beq.b .done
 move.l d0,FF1PO_PTR(a2)
 move.l d2,FF1PO_SIZE(a2)
 bra.b .done
.bad:
 moveq #0,d0
.done:
 movem.l (sp)+,d1-d2/a0-a2/a6
 rts

; A0 = allocation owner. Empty owners are harmless; exact size retained.
; D0-D7/A0-A6 preserved. Caller must first remove all references and flush
; changed code. Never release a published code/data block still in use.
FF1PublicRelease:
 movem.l d0-d1/a0-a2/a6,-(sp)
 move.l a0,a2
 move.l FF1PO_PTR(a2),d0
 beq.b .done
 move.l d0,a1
 move.l FF1PO_SIZE(a2),d0
 clr.l FF1PO_PTR(a2)
 clr.l FF1PO_SIZE(a2)
 move.l $4.w,a6
 jsr -210(a6)             ; FreeMem
.done:
 movem.l (sp)+,d0-d1/a0-a2/a6
 rts
 endc
