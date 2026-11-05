; Run after the ordinary real-DMA prefix comparison, using its original
; bitplanes as the second lane's start. No debugger writes, no host input.
vp_panel_check:
 movem.l d0-d7/a0-a6,-(sp)
 move.l #50,20(a6)
 movea.l vp_arena(pc),a0
 clr.w RT_CAPTURE_OWNER(a0)
 clr.w RT_VIEW_PHASE(a0)
 clr.w RT_TARGET_PHASE(a0)
 movea.l RT_HUNKS+16(a0),a1
 clr.b $1c5(a1) ; cockpit target panel, both lanes
 lea vp_expected(pc),a0
 lea vpp_reference(pc),a1
 moveq #83,d0
.copy:
 move.w (a0)+,(a1)+
 dbf d0,.copy
 lea vpp_reference(pc),a0
 clr.w 2(a0)
 move.b #2,(a0)
 move.w vp_expected+2(pc),d1
 beq .absent
 move.w $6c(a0),4(a0)
 move.w $76(a0),6(a0)
 bra .ready
.absent:
 move.w #$7ffe,4(a0) ; selected identity deliberately absent from this scene
 clr.w 6(a0)
.ready:
 ; Synthetic committed target: same identity, deliberately stale projection.
 lea vpp_world(pc),a1
 moveq #83,d0
.world:
 move.w (a0)+,(a1)+
 dbf d0,.world
 lea vpp_world(pc),a0
 addi.w #16,$80(a0)
 addi.w #8,$8a(a0)
 ; Reference draw uses independent native candidate geometry already captured.
 lea vpp_reference(pc),a0
 movea.l 8(a6),a1
 adda.l #$a99e,a1
 moveq #83,d0
.native_reference:
 move.w (a0)+,(a1)+
 dbf d0,.native_reference
 move.w vp_expected+2(pc),d1
 beq .reference_done
 movea.l 12(a6),a5
 adda.w #$38f6,a5
 movea.l 8(a6),a0
 adda.l #$a6e4,a0
 movem.l d7/a6,-(sp)
 jsr (a0)
 movem.l (sp)+,d7/a6
.reference_done:
 bsr vp_wait
 movea.l 16(a6),a2
 adda.l #64000,a2
 bsr vp_save_planes
 IFD VP_PANEL_SABOTAGE
 movea.l 16(a6),a0
 adda.l #64000,a0
 eori.b #1,(a0)
 ENDC
 movea.l 16(a6),a2
 bsr vp_restore_planes
 lea vpp_world(pc),a0
 movea.l 8(a6),a1
 adda.l #$a99e,a1
 moveq #83,d0
.native_world:
 move.w (a0)+,(a1)+
 dbf d0,.native_world
 movea.l vp_arena(pc),a0
 move.w #1,RT_CAPTURE_OWNER(a0)
 move.w #1,RT_VIEW_PHASE(a0)
 lea RT_VIEW(a0),a0
 lea vpp_world(pc),a1
 bsr target_view_reset
 tst.l d0
 bne .bad_state
 lea vp_camera(pc),a0
 lea vp_coords(pc),a1
 movea.l 12(a6),a2
 lea $3904(a2),a3
 bsr scene_state_build
 lea vp_reference(pc),a0
 jsr (a0)
 bsr vp_wait
 ; Geometry capture must agree before any display borrowing.
 movea.l vp_arena(pc),a0
 lea RT_VIEW(a0),a0
 lea vpp_actual(pc),a1
 bsr target_view_build
 move.w vp_expected+2(pc),d1
 beq .expect_absent
 cmpi.l #1,d0
 bne .bad_state
 lea vpp_reference(pc),a0
 lea vpp_actual(pc),a1
 ; Other candidates need not match: compare only selected drawing fields.
 move.w $80(a0),d0
 cmp.w $80(a1),d0
 bne .bad_state
 move.w $8a(a0),d0
 cmp.w $8a(a1),d0
 bne .bad_state
 move.l $94(a0),d0
 cmp.l $94(a1),d0
 bne .bad_state
 lea 18(a0),a0
 lea 18(a1),a1
 moveq #8,d0
.geometry:
 cmpm.w (a0)+,(a1)+
 bne .bad_state
 dbf d0,.geometry
 bra .draw
.expect_absent:
 tst.l d0
 bne .bad_state
.draw:
 movea.l 12(a6),a5
 adda.w #$38f6,a5
 bsr timing_view_panel
 bsr vp_wait
 movea.l 8(a6),a0
 adda.l #$a99e,a0
 lea vpp_world(pc),a1
 moveq #83,d0
.world_unchanged:
 cmpm.w (a0)+,(a1)+
 bne .bad_state
 dbf d0,.world_unchanged
 movea.l vp_arena(pc),a0
 tst.w RT_VIEW_PHASE(a0)
 bne .bad_state
 ; All real planes must match the native panel using the current projection.
 movea.l 32(a6),a1
 addq.l #8,a1
 move.l 40(a6),d3
 subq.w #1,d3
 movea.l 16(a6),a2
 adda.l #64000,a2
.planes:
 movea.l (a1)+,a0
 move.l 36(a6),d0
 subq.w #1,d0
.bytes:
 cmpm.b (a0)+,(a2)+
 bne .bad_pixels
 dbf d0,.bytes
 dbf d3,.planes
 lea vpp_passes(pc),a0
 addq.l #1,(a0)
 movea.l vp_arena(pc),a0
 clr.w RT_CAPTURE_OWNER(a0)
 movem.l (sp)+,d0-d7/a0-a6
 rts
.bad_state:
 moveq #-8,d0
 bra vp_fail
.bad_pixels:
 moveq #-9,d0
 bra vp_fail
 even
vpp_passes: dc.l 0
vpp_reference: ds.b 168
vpp_world: ds.b 168
vpp_actual: ds.b 168
