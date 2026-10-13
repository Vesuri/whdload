; Default-off D2: overlap CPU-only projection with display-buffer handover.
; The request to LoadView precedes this entry. A new native VBL field allows
; reuse of the old displayed buffer; otherwise retain the original line-256 wait.
; Native clear/sky drawing touch neither the projection inputs nor its outputs.
FF1C4PrepareRoad:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.w C4RoadPrefetchEnabled(pc),d0
 beq.w .done
 lea C4RoadField(pc),a0
 move.l C1Context(pc),(a0)
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
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 move.l sp,a1
 lea C4RoadRegisters(pc),a0
 moveq #30,d0
.copy:
 move.w (a1)+,(a0)+
 dbra d0,.copy
 lea 62(sp),sp
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
FF1C4DrawPreparedRoad:
 move.w C4RoadPrefetchEnabled(pc),-(sp)
 tst.w (sp)+
 beq.b .native
 ; The original entry pushes the word angle before its projection call.
 move.w 6(sp),-(sp)
 movem.l C4RoadRegisters(pc),d0-d7/a0-a6
 move.w C4RoadCCR(pc),ccr
 jmp $6b372
.native:
 jmp $6b368
C4RoadPrefetchEnabled: dc.w 0
C4RoadField: dc.l 0
C4RoadRegisters: ds.b 60
C4RoadCCR: dc.w 0
