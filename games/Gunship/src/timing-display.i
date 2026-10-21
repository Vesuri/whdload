; D2: retain the native copper list during enhanced 0658 flight. The task
; waits for VBL acknowledgement before reusing the old front buffer (D3 is
; separate). Menus/modal work keep the original screen-building routine.
timing_display_install:
 movem.l a0-a3,-(sp)
 movea.l RT_HUNKS(a0),a1
 cmpi.w #$4eb9,$44b4(a1)
 bne .bad
 lea $b7c(a1),a3
 cmpa.l $44b6(a1),a3
 bne .bad
 lea timing_display_native(pc),a0
 move.l a3,(a0)
 lea .patches(pc),a0
 jsr resload_Patch(a2)
 moveq #0,d0
 bra .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,a0-a3
 rts
.patches:
 PL_START
 PL_PS $44b4,timing_display_swap
 PL_END

timing_display_swap:
 movem.l d0-d7/a0-a6,-(sp)
 movea.l timing_runtime_arena(pc),a0
 cmpi.w #1,RT_CAPTURE_OWNER(a0)
 bne .native
 tst.w RT_BOUNDARY_PHASE(a0)
 bne .native
 ; FrontScreen can change while a system screen is in front. Yield rather
 ; than busy-spin, and fetch the current copper list only after it returns.
.front:
 movea.l $50b4(a4),a0
 movea.l $3c(a0),a0
 cmpa.l $47b0(a4),a0
 beq .ready
 bsr .wait
 bra .front
.ready:
 ; Finish the last cockpit DMA before publishing its bitmap to the VBL.
 movea.l 4.w,a6
 ; Native graphics.library base is the operand of the OwnBlitter wrapper.
 movea.l timing_runtime_arena(pc),a0
 movea.l RT_HUNKS(a0),a0
 adda.l #$867e,a0
 movea.l (a0),a0
 movea.l (a0),a6
 jsr -228(a6) ; WaitBlit
 move.l 64(sp),d7
 move.l d7,$49ac(a4)
 mulu #40,d7
 movea.l timing_runtime_arena(pc),a0
 movea.l RT_HUNKS(a0),a0
 movea.l $ba2(a0),a3 ; native bitmap-array relocation
 adda.l d7,a3
 ; Locate exactly one high/low move for each of the five display planes.
 ; No persistent addresses survive a native screen rebuild.
 lea timing_display_moves(pc),a2
 moveq #9,d0
.clear:
 clr.l (a2)+
 dbf d0,.clear
 movea.l $47b4(a4),a0
 movea.l 4(a0),a0
 movea.l 4(a0),a0
 moveq #0,d2
 move.w #255,d1
.scan:
 move.w (a0),d0
 cmpi.w #$ffff,d0
 beq .scanned
 subi.w #$e0,d0
 cmpi.w #18,d0
 bhi .next
 btst #0,d0
 bne .next
 add.w d0,d0
 lea timing_display_moves(pc),a2
 tst.l (a2,d0.w)
 bne .native
 lea 2(a0),a1
 move.l a1,(a2,d0.w)
 addq.w #1,d2
.next:
 addq.l #4,a0
 dbf d1,.scan
.scanned:
 cmpi.w #10,d2
 bne .native
 ; Preserve Screen.BitMap for subsequent native/modal screen rebuilds.
 movea.l $47b0(a4),a1
 adda.w #184,a1
 movea.l a3,a0
 moveq #9,d0
.bitmap:
 move.l (a0)+,(a1)+
 dbf d0,.bitmap
 lea timing_display_planes(pc),a1
 lea 8(a3),a0
 moveq #4,d0
.planes:
 move.l (a0)+,(a1)+
 dbf d0,.planes
 ; Payload precedes the single-word publication. VBL owns acknowledgement.
 lea timing_display_pending(pc),a0
 move.w #1,(a0)
.pending:
 bsr .wait
 move.w timing_display_pending(pc),d0
 bne .pending
 move.w #$8020,$dff096
 movem.l (sp)+,d0-d7/a0-a6
 rts
.native:
 movem.l (sp)+,d0-d7/a0-a6
 move.l timing_display_native(pc),-(sp)
 rts
.wait:
 movem.l d0-d1/a0-a1/a6,-(sp)
 movea.l timing_runtime_arena(pc),a0
 movea.l RT_HUNKS(a0),a0
 adda.l #$867e,a0
 movea.l (a0),a0
 movea.l (a0),a6
 jsr -270(a6) ; WaitTOF
 movem.l (sp)+,d0-d1/a0-a1/a6
 rts

; Called by the game's VBL server, already guarded by FrontScreen==ours.
; Palette moves and the pointers found by +00AB8 stay intact.
timing_display_vbl:
 move.w timing_display_pending(pc),d0
 beq .done
 lea timing_display_moves(pc),a0
 lea timing_display_planes(pc),a1
 moveq #4,d0
.plane:
 movea.l (a0)+,a2
 move.w (a1)+,(a2)
 movea.l (a0)+,a2
 move.w (a1)+,(a2)
 dbf d0,.plane
 lea timing_display_pending(pc),a0
 clr.w (a0)
.done:
 rts
 even
timing_display_native: dc.l 0
timing_display_pending: dc.w 0
timing_display_moves: ds.l 10
timing_display_planes: ds.l 5
