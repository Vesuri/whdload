; H3 fine-path: overlap CPU-only projection with display-buffer handover.
; The request to LoadView precedes this entry. A new native VBL field allows
; reuse of the old displayed buffer; otherwise retain the original line-256 wait.
; Native clear/sky drawing touch neither the projection inputs nor its outputs.
; This runs synchronously inside B8Draw, after B8PrepareRenderCopies. There is
; no pending work across a tick or a modal exit. The public lifetime reset table
; clears the field/register workspace; the nonzero immutable preset survives.
; CCR reads are required here: reading SR would trap through WHDLoad on 020+.
FF1RenderPrepareRoad:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 move.w FF1RenderRoadControl(pc),d0
 beq.w .done
 lea FF1RenderRoadField(pc),a0
 move.l schedule_context+FF1T_FIELDS(pc),(a0)
 move.w $6a67a,d0
 add.w $66f96,d0
 andi.w #$3ff,d0
 cmpi.w #$100,d0
 ble.b .angle
 cmpi.w #$300,d0
 bge.b .angle
 subi.w #$200,d0
.angle:
 move.w d0,-(sp)
 jsr $6a2d0
 addq.l #2,sp
 ; Preserve the full native projection result for its original call boundary.
 move.w ccr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 move.l sp,a1
 lea FF1RenderRoadRegisters(pc),a0
 moveq #30,d0
.copy:
 move.w (a1)+,(a0)+
 dbra d0,.copy
 lea 62(sp),sp
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
FF1RenderDrawPreparedRoad:
 move.w FF1RenderRoadControl(pc),-(sp)
 tst.w (sp)+
 beq.b .native
 ; The original entry pushes the word angle before its projection call.
 move.w 6(sp),-(sp)
 movem.l FF1RenderRoadRegisters(pc),d0-d7/a0-a6
 move.w FF1RenderRoadCCR(pc),ccr
 jmp $6b372
.native:
 jmp $6b368
; Native flag/clock routines draw into both pointer views. Earlier completion
; can expose the intermediate flag over the clock in the displayed bitmap.
; Compose both native passes on the back buffer, retaining the exact operations.
; The last blit's DMA pointers are latched before restoring the CPU-only view;
; B8Draw still waits for completion before releasing the blitter/publication.
FF1RenderPresentHUD:
 tst.w FF1RenderRoadControl(pc)
 beq.b .native
 move.l $226b2,-(sp)
 move.l $226ae,$226b2
 bsr.l FF1PresentFlag
 bsr.l FF1PresentClock
 move.l (sp)+,$226b2
 rts
.native:
 bsr.l FF1PresentFlag
 bra.l FF1PresentClock
FF1RenderRoadControl: dc.w 1
FF1RenderRoadField: dc.l 0
FF1RenderRoadRegisters: ds.b 60
FF1RenderRoadCCR: dc.w 0
