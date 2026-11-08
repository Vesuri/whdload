; Original presentation bug fixes, independent of CUSTOM2 and CPU selection.

; Blitter waits for routines that start a blit and return while it runs, so
; the CPU drew into, or reprogrammed, a blit still in progress; a CPU that
; overtakes the blitter (cached or Fast RAM code) corrupts the picture.
; Each keeps the native CCR. Sites (file or main-hunk offsets):
; - visual_clear_done replaces movem.l (sp)+,d0/a0 + rts: INTRO.AMI $1f88 and
;   $1fb4, TITLE.AMI $c008 (screen clears), main $2f6b2 (full-screen clear).
; - visual_scroll_start replaces move.w #$fa14,$58(a6): INTRO.AMI $1ff0 (one-
;   line scroll), TITLE.AMI $c1d0 (screen copy); the native rts follows.
; - visual_size_d7_done replaces move.w d7,$58(a0) + rts: TITLE.AMI $ad74,
;   $c956 and $ca98 (last plane copy, bobs), main $2f75e (partial clear).
; - visual_plane_copy replaces move.w d7,$58(a0) + lea $20d0(a1),a1 (with a
;   NOP): TITLE.AMI $ad24, $ad38, $ad4c and $ad60 (planes 1-4 of a copy).
; - visual_screen_copy_start replaces move.w #$c814,$58(a6): main $2f7c4 and
;   lomain.ami $47aa (runtime $4baa) (full-screen copies); the native rts
;   follows.
visual_clear_done:
 movem.l (a7)+,d0/a0
 bra.b visual_blit_wait
visual_scroll_start:
 move.w #$fa14,$58(a6)
 bra.b visual_blit_wait
visual_screen_copy_start:
 move.w #$c814,$58(a6)
 bra.b visual_blit_wait
visual_size_d7_done:
 move.w d7,$58(a0)
 bra.b visual_blit_wait
visual_plane_copy:
 move.w d7,$58(a0)
 bsr.b visual_blit_wait
 lea $20d0(a1),a1
 rts
visual_blit_wait:
 move.w sr,-(a7)
 btst #6,$dff002
.wait:
 btst #6,$dff002
 bne .wait
 move.w (a7)+,ccr
 rts

; Compare full 16.16 separation before rounding. D0 must still carry the
; difference of segment indices for the native forward geometry lookup.
visual_actor_visibility:
 move.l 4(a1),d0
 move.l d0,d2
 swap d0
 sub.w $a5d1e,d0
visual_ref_0 equ *-4
 move.l d2,-(a7)
 sub.l $a5d1e,d2
visual_ref_1 equ *-4
 bmi .rear
 cmpi.l #$1e0000,d2 ; fixed 30-segment horizon, safe indices 0..30
 bge .hidden
 move.l (a7)+,d2
 jmp $89e70 ; includes the selected native/enhanced lean path
visual_ref_2 equ *-4
.rear:
 cmpi.l #-$100000,d2
 blt .rear_far
 move.w d1,-(a7)
 move.w $a5d72,d1
visual_ref_3 equ *-4
 cmp.w $12(a1),d1
 blt .mirror
 cmpi.l #-$10000,d2 ; stable one-segment close-behind boundary
 ble .mirror
 move.w (a7)+,d1
.hidden:
 move.l (a7)+,d2
 jmp $8a126
visual_ref_4 equ *-4
.mirror:
 move.w (a7)+,d1
 move.l (a7)+,d2
 jsr $88d50
visual_ref_5 equ *-4
 jmp $89f90
visual_ref_6 equ *-4
.rear_far:
 move.l (a7)+,d2
 jmp $89f90
visual_ref_7 equ *-4

; A1 has already advanced to the following segment and wrapped at 255.
; Its height byte describes the interval the camera is moving through.
; Replace EXT.W/BEQ: zero also safely follows the native positive multiply.
; Do not advance A1: forward accumulation must consume that same interval.
pl_visual_height:
 PL_START
 PL_PS $97A6,visual_height_interval
 PL_END
visual_height_interval:
 move.b 1(a1),d3
 ext.w d3
 rts
