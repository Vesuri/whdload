 IFD VP_TIMING
VP_ROW_SIZE equ 184
 ELSE
VP_ROW_SIZE equ 176
 ENDC
; Diagnostic-only guest twin. Never linked into distributed slaves.
visibility_probe_install:
 movem.l d0-d7/a0-a6,-(sp)
.base:
 lea .base(pc),a3
 adda.l #pl_gamemule_658-.base,a3
 cmpa.l a3,a0
 bne .done
 lea .base(pc),a3
 adda.l #timing_runtime_arena-.base,a3
 movea.l (a3),a3
 move.l a3,d0
 beq .done
 lea vp_arena(pc),a5
 move.l a3,(a5)
 lea vp_result(pc),a5
 move.l RT_HUNKS(a3),8(a5)
 move.l RT_HUNKS+24(a3),12(a5)
 movea.l 4.w,a6
 move.l #132000,d0
 move.l #MEMF_PUBLIC|MEMF_CLEAR,d1
 jsr _LVOAllocMem(a6)
 move.l d0,16(a5)
 beq .bad
 movea.l 8(a5),a0
 movea.l 12(a5),a1
 lea vp_raster(pc),a2
 bsr visibility_raster_prepare
 tst.l d0
 bne .bad
 movea.l 8(a5),a0
 movea.l 12(a5),a1
 lea vp_target(pc),a2
 bsr target_select_prepare
 tst.l d0
 bne .bad
 ; Independent exact native prefix, captured before installing our panel hook.
 movea.l 8(a5),a0
 adda.l #$5c04,a0
 lea vp_reference(pc),a1
 moveq #$74/2-1,d0
.copy:
 move.w (a0)+,(a1)+
 dbf d0,.copy
 move.l #$4cdf78f8,(a1)+
 move.w #$4e75,(a1)+
 movea.l 40(sp),a2
 lea .patch(pc),a0
 movea.l 8(a5),a1
 jsr resload_Patch(a2)
 move.l #1,20(a5)
 bra .done
.bad:
 move.l #-1,20(a5)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
.patch:
 PL_START
 PL_PS $5c78,visibility_probe_entry
 PL_END

visibility_probe_entry:
 ; Own this diagnostic session forever. DMA continues; no VBL state changes.
 move.w #$7fff,$dff09a
 lea vp_result(pc),a6
 move.l #2,20(a6)
 bsr vp_wait
 IFD VP_TIMING
 bsr vp_field_edge
 bsr vp_clock_start
 moveq #9,d7
.calibrate:
 bsr vp_field_edge
 dbf d7,.calibrate
 bsr vp_clock_stop
 lea vp_calibration(pc),a0
 move.l d0,(a0)
 bsr vp_clock_start
 bsr vp_clock_stop
 lea vp_calibration(pc),a0
 move.l d0,4(a0)
 ENDC
 moveq #0,d7
.view:
 move.l #10,20(a6)
 IFD VP_OWNER
 movea.l timing_runtime_arena(pc),a0
 clr.w RT_CAPTURE_OWNER(a0)
 clr.w RT_TARGET_PHASE(a0)
 clr.w RT_BOUNDARY_PHASE(a0)
 ENDC
 IFD VP_HEADING
 movea.l vp_arena(pc),a0
 clr.w RT_CAPTURE_OWNER(a0)
 clr.w RT_VIEW_PHASE(a0)
 clr.w RT_TARGET_PHASE(a0)
 move.w d7,d0
 lsl.w #5,d0
 addi.b #64,d0
 movea.l 12(a6),a5
 move.b d0,$3ce3(a5)
 move.l #$7fff7fff,$3b88(a5) ; native proximity filter uses player XY
 move.w #536,$3ba4(a5)
 ENDC
 movea.l 12(a6),a5
 move.w d7,d0
 lsr.w #3,d0
 move.b d0,$3b9e(a5)
 lea $3904(a5),a3
 lea vp_camera(pc),a0
 move.w #$7fff,(a0)
 move.w #$7fff,2(a0)
 move.w #536,4(a0)
 move.w d7,d0
 lsl.w #8,d0
 lsl.w #5,d0
 neg.w d0
 move.w d0,6(a0)
 clr.l 8(a0)
 lea vp_coords(pc),a1
 move.w #$7eff,d0
 moveq #5,d1
.xy:
 move.w d0,(a1)
 move.w d0,12(a1)
 move.w #544,24(a1)
 addi.w #128,d0
 addq.l #2,a1
 dbf d1,.xy
 ; The special object shares native split coordinate bytes.
 move.b #$80,$3be3(a5)
 move.b #$7f,$3c5d(a5)
 move.b #$80,$3c63(a5)
 move.b #$7f,$3cdd(a5)
 move.b #2,$3ddd(a5)
 move.b #$18,$3d5d(a5)
 movea.l 8(a6),a0
 adda.l #$ba08,a0
 move.w #$3f,(a0)
 movea.l 8(a6),a0
 adda.l #$a99e,a0
 lea vp_target+WT_STATE(pc),a1
 moveq #83,d0
.seed:
 move.w (a0)+,(a1)+
 dbf d0,.seed
 lea vp_target+WT_STATE(pc),a1
 clr.w 2(a1)
 moveq #0,d0
 moveq #4,d1
 lea 8(a1),a2
.layout:
 move.w d0,(a2)+
 addi.w #18,d0
 dbf d1,.layout
 movea.l 8(a6),a0
 adda.l #$a99e,a0
 moveq #83,d0
.seed_native:
 move.w (a1)+,(a0)+
 dbf d0,.seed_native
 ; Bind and retain identical initial bitplanes for both drawing passes.
 movea.l 8(a6),a0
 adda.l #$84e2,a0
 jsr (a0)
 move.l a1,32(a6)
 moveq #0,d0
 move.w (a1),d0
 mulu.w 2(a1),d0
 move.l d0,36(a6)
 moveq #0,d1
 move.b 5(a1),d1
 move.l d1,40(a6)
 beq vp_bad_bitmap
 cmpi.l #6,d1
 bhi vp_bad_bitmap
 move.l d0,d2
 mulu.w d1,d2
 cmpi.l #64000,d2
 bhi vp_bad_bitmap
 tst.l d0
 beq vp_bad_bitmap
 movea.l 16(a6),a2
 bsr vp_save_planes
 lea vp_camera(pc),a0
 lea vp_coords(pc),a1
 movea.l 12(a6),a2
 lea $3904(a2),a3
 bsr scene_state_build
 lea vp_reference(pc),a0
 IFD VP_TIMING
 bsr vp_clock_start
 ENDC
 jsr (a0)
 bsr vp_wait
 IFD VP_TIMING
 bsr vp_clock_stop
 lea vp_times(pc),a0
 move.l d0,(a0)
 ENDC
 move.l #20,20(a6)
 movea.l 8(a6),a0
 adda.l #$a99e,a0
 lea vp_expected(pc),a1
 moveq #83,d0
.capture:
 move.w (a0)+,(a1)+
 dbf d0,.capture
 lea vp_expected(pc),a3
 moveq #0,d5
 move.w 2(a3),d5
 cmpi.w #5,d5
 bhi vp_bad_count
 tst.w d5
 beq .empty
 addq.l #1,28(a6)
.empty:
 lea vp_pixels(pc),a2
 clr.l (a2)
 clr.w 4(a2)
 moveq #0,d4
 subq.w #1,d5
 bmi .sampled
.pixels:
 lea vp_expected+$80(pc),a3
 move.w 0(a3,d4.w),d0
 move.w 10(a3,d4.w),d1
 movea.l 8(a6),a0
 adda.l #$825e,a0
 jsr (a0)
 move.b d0,(a2)+
 addq.w #2,d4
 dbf d5,.pixels
.sampled:
 IFD VP_OWNER
 ; Preserve the native selection result, then restore its original seed.
 movea.l 8(a6),a0
 adda.l #$a58c,a0
 jsr (a0)
 movea.l 8(a6),a0
 adda.l #$a99e,a0
 lea vp_expected(pc),a1
 moveq #83,d0
.selected:
 move.w (a0)+,(a1)+
 dbf d0,.selected
 movea.l 8(a6),a0
 adda.l #$a99e,a0
 lea vp_target+WT_STATE(pc),a1
 moveq #83,d0
.reset_target:
 move.w (a1)+,(a0)+
 dbf d0,.reset_target
 ENDC
 movea.l 16(a6),a2
 adda.l #64000,a2
 bsr vp_save_planes
 movea.l 16(a6),a2
 bsr vp_restore_planes
 move.l #30,20(a6)
 lea vp_raster(pc),a0
 lea vp_target(pc),a1
 lea vp_camera(pc),a2
 lea vp_coords(pc),a3
 IFD VP_TIMING
 bsr vp_clock_start
 ENDC
 IFD VP_OWNER
 movea.l 12(a6),a0
 lea $3b88(a0),a0
 move.l #$7fff7fff,(a0)
 move.w #512,28(a0)
 clr.b 26(a0)
 move.w d7,d0
 lsl.w #5,d0
 move.b d0,53(a0)
 clr.b 54(a0)
 clr.b 55(a0)
 lea vp_coords(pc),a0
 movea.l 8(a6),a1
 adda.l #$c6a0,a1
 moveq #17,d0
.world_coords:
 move.w (a0)+,(a1)+
 dbf d0,.world_coords
 movea.l timing_runtime_arena(pc),a0
 move.w #1,RT_CAPTURE_OWNER(a0)
 IFD VP_RETAINED
 cmpi.w #8,d7
 blo .ordinary_owner
 clr.w RT_CAPTURE_OWNER(a0)
 move.w #4,RT_BOUNDARY_PHASE(a0)
.ordinary_owner:
 ENDC
 move.w #2,RT_SCHEDULER+TS_STATE(a0)
 move.w #1,RT_CLOCK+TC_ACTIVE(a0)
 move.w #1,RT_HISTORY+TH_ACTIVE(a0)
 move.w #1,RT_COMMANDS+CQ_ACTIVE(a0)
 move.w #1,RT_SCHEDULER+TS_DUE(a0)
 move.w #3,RT_CONSUMER+TF_PHASE(a0)
 moveq #0,d0
 move.w d7,d0
 addq.l #1,d0
 move.l d0,RT_SCHEDULER+TS_FIELD(a0)
 move.l d0,RT_CONSUMER+TF_FIELD(a0)
 move.l d0,RT_RECORD+TR_FIELD(a0)
 bsr timing_runtime_target
 tst.l d0
 bne vp_bad_step
 ; Render hooks must not modify the newly published world target.
 bsr timing_render_collect
 bsr timing_render_select
 movea.l timing_runtime_arena(pc),a0
 bsr timing_runtime_target
 cmpi.l #-3,d0
 bne vp_bad_step
 movea.l timing_runtime_arena(pc),a0
 lea RT_TARGET(a0),a0
 lea vp_target(pc),a1
 move.w #WT_SIZE/2-1,d0
.retain:
 move.w (a0)+,(a1)+
 dbf d0,.retain
 moveq #0,d0
 ELSE
 IFD VP_HEADING
 movea.l vp_arena(pc),a0
 movea.l 12(a6),a1
 move.b $3ce3(a1),RT_SCRIPT_POSE+6(a0)
 eori.b #128,$3ce3(a1) ; world heading differs from the rendered forecast
 IFD VP_HEADING_SABOTAGE
 eori.b #128,RT_SCRIPT_POSE+6(a0)
 ENDC
 move.w #1,RT_CAPTURE_OWNER(a0)
 move.w #1,RT_VIEW_PHASE(a0)
 clr.w RT_TARGET_PHASE(a0)
 lea RT_VIEW(a0),a0
 lea vp_expected(pc),a1
 bsr target_view_reset
 lea vp_camera(pc),a0
 lea vp_coords(pc),a1
 movea.l 12(a6),a2
 lea $3904(a2),a3
 bsr scene_state_build
 lea vp_reference(pc),a0
 jsr (a0)
 bsr vp_wait
 movea.l 12(a6),a0
 move.w d7,d0
 lsl.w #5,d0
 addi.b #64,d0
 eori.b #128,d0
 cmp.b $3ce3(a0),d0
 bne vp_bad_step
 moveq #0,d0
 ELSE
 bsr visibility_raster_step
 ENDC
 ENDC
 tst.l d0
 bne vp_bad_step
 IFD VP_TIMING
 bsr vp_clock_stop
 lea vp_times(pc),a0
 move.l d0,4(a0)
 ENDC
 IFD VP_SABOTAGE
 movea.l 16(a6),a0
 adda.l #64000,a0
 eori.b #1,(a0)
 ENDC
 move.l #40,20(a6)
 IFND VP_HEADING
 lea vp_expected(pc),a0
 lea vp_target+WT_STATE(pc),a1
 moveq #83,d0
.compare:
 cmpm.w (a0)+,(a1)+
 bne vp_bad_candidates
 dbf d0,.compare
 IFD VP_OWNER
 movea.l 8(a6),a0
 adda.l #$a99e,a0
 lea vp_expected(pc),a1
 moveq #83,d0
.native_publication:
 cmpm.w (a0)+,(a1)+
 bne vp_bad_candidates
 dbf d0,.native_publication
 ENDC
 lea vp_pixels(pc),a0
 lea vp_target+WT_PIXELS(pc),a1
 moveq #2,d0
.compare_pixels:
 cmpm.w (a0)+,(a1)+
 bne vp_bad_pixels
 dbf d0,.compare_pixels
 ENDC
 ; Compare every byte of every real DMA output plane.
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
 bne vp_bad_planes
 dbf d0,.bytes
 dbf d3,.planes
 IFD VP_PANEL
 bsr vp_panel_check
 ENDC
 movea.l 16(a6),a1
 adda.l #128000,a1
 move.w d7,d0
 mulu.w #VP_ROW_SIZE,d0
 adda.l d0,a1
 lea vp_expected(pc),a0
 moveq #83,d0
.record:
 move.w (a0)+,(a1)+
 dbf d0,.record
 lea vp_pixels(pc),a0
 move.l (a0)+,(a1)+
 move.w (a0),(a1)+
 clr.w (a1)+
 IFD VP_TIMING
 lea vp_times(pc),a0
 move.l (a0)+,(a1)+
 move.l (a0),(a1)
 ENDC
 addq.l #1,24(a6)
 addq.w #1,d7
 cmpi.w #16,d7
 bne .view
 move.l #100,20(a6)
 bra vp_done
vp_bad_bitmap: moveq #-2,d0
 bra vp_fail
vp_bad_count: moveq #-3,d0
 bra vp_fail
vp_bad_step: moveq #-4,d0
 bra vp_fail
vp_bad_candidates: moveq #-5,d0
 bra vp_fail
vp_bad_pixels: moveq #-6,d0
 bra vp_fail
vp_bad_planes: moveq #-7,d0
vp_fail:
 move.l d0,20(a6)
vp_done:
 bra.s vp_done
vp_wait:
 tst.w $dff002
.wait:
 btst #6,$dff002
 bne .wait
 rts
; a2=packed buffer, a6=result. Preserve d7/a6; clobber d0-d3/a0-a2.
vp_save_planes:
 movea.l 32(a6),a1
 addq.l #8,a1
 move.l 40(a6),d3
 subq.w #1,d3
.plane:
 movea.l (a1)+,a0
 move.l 36(a6),d0
 subq.w #1,d0
.byte:
 move.b (a0)+,(a2)+
 dbf d0,.byte
 dbf d3,.plane
 rts
vp_restore_planes:
 movea.l 32(a6),a1
 addq.l #8,a1
 move.l 40(a6),d3
 subq.w #1,d3
.plane:
 movea.l (a1)+,a0
 move.l 36(a6),d0
 subq.w #1,d0
.byte:
 move.b (a2)+,(a0)+
 dbf d0,.byte
 dbf d3,.plane
 rts
 even
vp_result:
 dc.b 'GSVP0001'
 ds.l 9 ; h0,h6,buffer,status,completed,nonempty,bitmap,plane bytes,depth
vp_reference: ds.b $7a
vp_raster: ds.b VR_SIZE
vp_target: ds.b WT_SIZE
vp_camera: ds.b 12
vp_coords: ds.b 36
vp_expected: ds.b WT_STATE_SIZE
vp_pixels: ds.b 6
 even



 IFD VP_TIMING
; CIAB timers cascade to a 32-bit E-clock downcounter. Diagnostic-only;
; interrupts are already disabled and the test never resumes gameplay.
vp_clock_start:
 clr.b $bfde00
 move.b #$40,$bfdf00
 move.b #$ff,$bfd400
 move.b #$ff,$bfd500
 move.b #$ff,$bfd600
 move.b #$ff,$bfd700
 move.b #$51,$bfdf00
 move.b #$11,$bfde00
 rts
vp_clock_stop:
 clr.b $bfde00
 move.b #$40,$bfdf00
 moveq #0,d0
 move.b $bfd700,d0
 lsl.l #8,d0
 move.b $bfd600,d0
 lsl.l #8,d0
 move.b $bfd500,d0
 lsl.l #8,d0
 move.b $bfd400,d0
 not.l d0
 rts
vp_field_edge:
.high:
 btst #0,$dff005
 beq .high
.low:
 btst #0,$dff005
 bne .low
 rts
 even
vp_calibration: ds.l 2
vp_times: ds.l 2
 ENDC

 IFD VP_PANEL
 include "target_panel_probe_c.i"
 ENDC

 even
vp_arena: dc.l 0
