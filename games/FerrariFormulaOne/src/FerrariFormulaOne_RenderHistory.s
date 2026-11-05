; B8 candidate adapter; enabled only by an explicit experimental host.
; History and render scratch live with the public-memory candidate code.
; Native simulation arrays are never temporarily swapped or overwritten.
 IFD FF1_RENDER_POSES
B8InvalidateRenderHistory:
 move.l a0,-(sp)
 move.w ccr,-(sp)
 lea (B8HistoryValid.l,pc),a0
 clr.w (a0)
 move.w (sp)+,ccr
 move.l (sp)+,a0
 rts
B8TowEntry:
 bsr.b B8InvalidateRenderHistory
 link a6,#-4
 move.w $32fbc,d0
 jmp $694a0
B8PoseTick:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 lea (B8Epoch.l,pc),a0
 move.w $1bee8,d0
 move.w $1c1c2,d1
 move.w $1c1c4,d2
 move.w $1c21e,d3
 cmp.w (a0),d0
 bne.b .reset
 cmp.w 2(a0),d1
 bne.b .reset
 cmp.w 4(a0),d2
 bne.b .reset
 cmp.w 6(a0),d3
 beq.b .epoch
.reset:
 move.w d0,(a0)
 move.w d1,2(a0)
 move.w d2,4(a0)
 move.w d3,6(a0)
 lea (B8HistoryValid.l,pc),a0
 clr.w (a0)
.epoch:
 tst.w B8HistoryValid(pc)
 beq.b .capture
 tst.w events_pulse(pc)
 beq.b .done
.capture:
 lea (B8Previous.l,pc),a0
 lea (B8Current.l,pc),a1
 moveq #2,d7
.car:
 move.l (a1),(a0)
 move.l 4(a1),4(a0)
 move.l 8(a1),8(a0)
 lea $6a60a,a2
 move.w (a2,d7.w),(a1)
 move.w 16(a2,d7.w),2(a1)
 move.w 32(a2,d7.w),4(a1)
 move.w 96(a2,d7.w),6(a1)
 move.w 112(a2,d7.w),8(a1)
 lea $2268e,a2
 move.w (a2,d7.w),10(a1)
 tst.w B8HistoryValid(pc)
 bne.b .next
 move.l (a1),(a0)
 move.l 4(a1),4(a0)
 move.l 8(a1),8(a0)
.next:
 lea FF1RP_SIZE(a0),a0
 lea FF1RP_SIZE(a1),a1
 addq.w #2,d7
 cmpi.w #16,d7
 blo.b .car
 lea (B8HistoryValid.l,pc),a0
 move.w #1,(a0)
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts

B8PrepareRenderCopies:
 movem.l d0-d7/a0-a6,-(sp)
 ; Include native object sorting scratch around the pose arrays. Only selected
 ; projection outputs are copied back, never the authoritative pose words.
 lea $6a5aa,a0
 lea (B8RenderArena.l,pc),a1
 moveq #55,d0
.copy:
 move.l (a0)+,(a1)+
 dbra d0,.copy
 lea (schedule_context.l,pc),a0
 bsr.l FF1TimeDue
 tst.l d2
 bne.b .late
 cmpi.l #FF1T_20MS_UNITS*5,d1
 bhs.b .late
 mulu.l #100,d1
 divu.l #FF1T_20MS_UNITS*5,d1
 move.w FF1T_PHASE_MS(a0),d6
 add.w d1,d6
 cmpi.w #100,d6
 bls.b .blend
.late:
 moveq #100,d6
.blend:
 lea (B8Previous.l,pc),a0
 lea (B8Current.l,pc),a1
 lea (B8Blended.l,pc),a2
 lea $2180c,a3
 lea (B8RenderArena+96.l,pc),a4
 moveq #2,d7
.car:
 move.w d6,d0
 move.w $2268c,d1
 bsr.l FF1BlendRenderPose
 move.w (a2),(a4,d7.w)
 move.w 2(a2),16(a4,d7.w)
 move.w 4(a2),32(a4,d7.w)
 move.w 6(a2),96(a4,d7.w)
 move.w 8(a2),112(a4,d7.w)
 lea FF1RP_SIZE(a0),a0
 lea FF1RP_SIZE(a1),a1
 addq.w #2,d7
 cmpi.w #16,d7
 blo.b .car
 movem.l (sp)+,d0-d7/a0-a6
 rts

B8PublishProjection:
 ; Displaced h173 tail: publish only the renderer's ID, depth and lateral
 ; arrays, then retain the native road projection. The car arrays remain untouched.
 movem.l d0/a0-a1,-(sp)
 move.w ccr,-(sp)
 lea (B8RenderArena.l,pc),a0
 lea $6a5aa,a1
 moveq #23,d0
.first:
 move.l (a0)+,(a1)+
 dbra d0,.first
 lea (B8RenderArena+144.l,pc),a0
 lea $6a63a,a1
 moveq #11,d0
.second:
 move.l (a0)+,(a1)+
 dbra d0,.second
 move.w (sp)+,ccr
 movem.l (sp)+,d0/a0-a1
 jmp $6b168

B8InstallRenderCopies:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.l #$2a7c0006,$6a2d0
 bne.w .bad
 cmpi.w #$a61a,$6a2d4
 bne.w .bad
 cmpi.l #$4ef90006,$6a5a4
 bne.w .bad
 cmpi.w #$b168,$6a5a8
 bne.w .bad
 cmpi.l #$d3fc0006,$69ce4
 bne.w .bad
 cmpi.w #$a66a,$69ce8
 bne.w .bad
 cmpi.l #$d1fc0006,$6c6f4
 bne.w .bad
 cmpi.w #$a60a,$6c6f8
 bne.w .bad
 cmpi.l #$d1fc0006,$6c73a
 bne.w .bad
 cmpi.w #$a62a,$6c73e
 bne.w .bad
 cmpi.l #$d3fc0006,$6c796
 bne.w .bad
 cmpi.w #$a61a,$6c79a
 bne.w .bad
 cmpi.l #$30390006,$654ec
 bne.w .bad
 cmpi.w #$6f88,$654f0
 bne.w .bad
 cmpi.l #$4e56fffc,$69496
 bne.w .bad
 cmpi.l #$30390003,$6949a
 bne.w .bad
 cmpi.w #$2fbc,$6949e
 bne.w .bad
 lea (B8TowEntry.l,pc),a0
 move.w #$4ef9,$69496
 move.l a0,$69498
 lea (B8RenderArena+112.l,pc),a0
 move.l a0,$6a2d2
 lea (B8PublishProjection.l,pc),a0
 move.l a0,$6a5a6
 lea (B8RenderArena+192.l,pc),a0
 move.l a0,$69ce6
 lea (B8RenderArena+96.l,pc),a0
 move.l a0,$6c6f6
 lea (B8RenderArena+128.l,pc),a0
 move.l a0,$6c73c
 lea (B8RenderArena+112.l,pc),a0
 move.l a0,$6c798
 ; Buffer publication belongs to drawing, not to catch-up simulation ticks.
 move.w #$4ef9,$654ec
 move.l #$65542,$654ee
 bra.b .done
.bad:
 lea (error.l,pc),a0
 move.l #38,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts

B8HistoryValid: dc.w 0
B8Epoch: ds.w 4
B8Previous: ds.b FF1RP_SIZE*7
B8Current: ds.b FF1RP_SIZE*7
B8Blended: ds.b FF1RP_SIZE
B8RenderArena: ds.b 224
 ENDC
