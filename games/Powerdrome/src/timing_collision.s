 machine 68020
; Track collision ($fa18, once per 20 ms world step) where its native outcome depends on
; how much movement one call sees. Natively one call covers one rendered frame, about
; 90 ms on the A500 (11.4 fps); here it covers one world step of four clock units.
TIMING_COLLISION_NATIVE = 18           ; clock units of movement in a native A500 frame
TIMING_COLLISION_STEP = 4              ; clock units of movement in a world step
TIMING_COLLISION_CRASH = -819200       ; native depth at $ad5a that ends in a crash

; $ad5a: CMP.L #-819200,d4 before $ac72 returns the crash distance $7fffffff. d4 is the
; contacted plane's distance after this step's movement, d0 its index and a0 the track
; section's planes. Compare the distance before the step ($186..$18a, saved at $cd78) plus
; 18/4 of this step's travel towards the plane, the depth one A500 frame of the same
; motion reaches. 64-bit, so no product can wrap. Only the flags for the native BGT.S at
; $ad60 change; every register is kept.
timing_collision_depth
 movem.l d0-d3/d5-d6/a0,-(sp)
 mulu.w #10,d0
 adda.l d0,a0
 move.w (a0),d1
 muls.w $186(a6),d1
 move.w 2(a0),d2
 muls.w $188(a6),d2
 add.l d2,d1
 move.w 4(a0),d2
 muls.w $18a(a6),d2
 add.l d2,d1
 sub.l 6(a0),d1                 ; distance before the step
 move.l d4,d3
 sub.l d1,d3                    ; travel this step (negative: into the plane)
 muls.l #TIMING_COLLISION_NATIVE,d2:d3
 move.l d1,d6
 muls.l #TIMING_COLLISION_STEP,d5:d6
 add.l d6,d3
 addx.l d5,d2                   ; d2:d3 = 4 * native-frame depth
 moveq #0,d0
 tst.l d2
 bpl.s .compare
 cmp.l #-1,d2
 bne.s .deep
 cmp.l #TIMING_COLLISION_CRASH*TIMING_COLLISION_STEP,d3
 bhi.s .compare
.deep
 move.l #TIMING_COLLISION_CRASH,d0
.compare
 cmp.l #TIMING_COLLISION_CRASH,d0
 movem.l (sp)+,d0-d3/d5-d6/a0
 rts

; $fb3e: BSR $16e6c / BRA.S $fb84, floor contact on a flagged track tile while moving.
; $16e6c flashes the palette with display waits. Like the wall-contact flash at $fb64, it
; belongs to control epochs. $fb84 follows either way; its damage gate
; (timing_world20_damage) returns from the collision routine between control epochs.
timing_collision_floor
 bsr timing_world20_test_control
 beq.s .damage
 bsr timing_collision_floor_flash
.damage
 bra.w timing_collision_damage

timing_collision_floor_flash dc.w $4ef9
 dc.l 0
timing_collision_damage dc.w $4ef9
 dc.l 0
