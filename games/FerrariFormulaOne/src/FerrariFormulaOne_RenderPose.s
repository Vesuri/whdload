; B8: opponent presentation poses, separate from authoritative car arrays.
; 68020 only. This module installs no hooks and is absent unless enabled.
;
; Pose: segment.w, lateral.w, longitudinal.w, heading.w, local-heading.w,
; status.w. Angles use 1024 units/revolution. A render pose may have a negative
; longitudinal coordinate: at a section crossing the old endpoint is expressed
; in the CURRENT section's basis, so interpolation never blends unrelated axes.
;
; FF1BlendRenderPose: A0 previous, A1 current, A2 output (12 bytes), A3 native
; Q15 sine table (1024 words plus the cosine extension), D0.w alpha 0..100,
; D1.w track section count. D0 returns 0=blend, 1=reset/snap. All other registers
; are preserved. Input/output must be distinct. No input, RNG, clock or DMA writes.
; The caller supplies consecutive native 100 ms endpoints and invalidates history
; on cuts, tow, load and driving-epoch changes. Status changes and nonadjacent
; sections defensively snap here. The player must bypass this delayed history.

 IFD FF1_RENDER_POSES
FF1RP_SEGMENT equ 0
FF1RP_X equ 2
FF1RP_Z equ 4
FF1RP_YAW equ 6
FF1RP_LOCAL equ 8
FF1RP_STATUS equ 10
FF1RP_SIZE equ 12

FF1BlendRenderPose:
 movem.l d1-d7/a0-a6,-(sp)
 moveq #0,d7
 move.w d0,d7
 cmpi.w #100,d7
 bls.b .alpha
 moveq #100,d7
.alpha:
 move.l (a1),(a2)
 move.l 4(a1),4(a2)
 move.l 8(a1),8(a2)
 tst.w FF1RP_STATUS(a1)
 bne.w .snap
 move.w FF1RP_STATUS(a0),d0
 cmp.w FF1RP_STATUS(a1),d0
 bne.w .snap
 move.w FF1RP_SEGMENT(a1),d6
 sub.w FF1RP_SEGMENT(a0),d6
 beq.w .same
 cmpi.w #1,d6
 beq.b .forward
 cmpi.w #-1,d6
 beq.b .backward
 subq.w #1,d1
 cmp.w d1,d6
 beq.b .backward
 neg.w d1
 cmp.w d1,d6
 bne.w .snap
.forward:
 moveq #1,d6
 bra.b .transform
.backward:
 moveq #-1,d6
.transform:
 ; Current basis minus previous basis. Use exactly the native Q15 table.
 move.w FF1RP_YAW(a1),d4
 sub.w FF1RP_LOCAL(a1),d4
 sub.w FF1RP_YAW(a0),d4
 add.w FF1RP_LOCAL(a0),d4
 andi.w #1023,d4
 move.w d4,d0
 add.w d0,d0
 move.w (a3,d0.w),d2
 move.w 512(a3,d0.w),d3
 move.w FF1RP_X(a0),d0
 ext.l d0
 move.w FF1RP_Z(a0),d1
 ext.l d1
 tst.w d6
 bmi.b .rotate
 subi.l #512,d1
.rotate:
 ; Rotate into the new section; round each product as native trig does.
 move.l d0,d5
 muls.w d3,d5
 asr.l #8,d5
 asr.l #7,d5
 move.l d1,d6
 muls.w d2,d6
 asr.l #8,d6
 asr.l #7,d6
 sub.l d6,d5
 muls.w d2,d0
 asr.l #8,d0
 asr.l #7,d0
 muls.w d3,d1
 asr.l #8,d1
 asr.l #7,d1
 add.l d0,d1
 ; A backward crossing has its new origin 512 units behind the old one.
 move.w FF1RP_SEGMENT(a1),d0
 sub.w FF1RP_SEGMENT(a0),d0
 cmpi.w #-1,d0
 beq.b .back_offset
 cmpi.w #1,d0
 beq.b .rotated
 tst.w d0
 bmi.b .rotated
.back_offset:
 addi.l #512,d1
.rotated:
 move.l d5,d0
 bra.b .positions
.same:
 move.w FF1RP_X(a0),d0
 ext.l d0
 move.w FF1RP_Z(a0),d1
 ext.l d1
 moveq #0,d4
.positions:
 move.l d1,d5
 move.w FF1RP_X(a1),d1
 ext.l d1
 bsr.w .linear
 move.w d0,FF1RP_X(a2)
 move.l d5,d0
 move.w FF1RP_Z(a1),d1
 ext.l d1
 bsr.w .linear
 move.w d0,FF1RP_Z(a2)
 move.w FF1RP_YAW(a0),d0
 move.w FF1RP_YAW(a1),d1
 bsr.b .angle
 move.w d0,FF1RP_YAW(a2)
 move.w FF1RP_LOCAL(a0),d0
 sub.w d4,d0
 move.w FF1RP_LOCAL(a1),d1
 bsr.b .angle
 move.w d0,FF1RP_LOCAL(a2)
 moveq #0,d0
 bra.b .done
.snap:
 moveq #1,d0
.done:
 movem.l (sp)+,d1-d7/a0-a6
 rts
.angle:
 andi.l #1023,d0
 sub.w d0,d1
 addi.w #512,d1
 andi.w #1023,d1
 subi.w #512,d1
 ext.l d1
 muls.l d7,d1
 divs.l #100,d1
 add.l d1,d0
 andi.l #1023,d0
 rts
.linear:
 sub.l d0,d1
 muls.l d7,d1
 divs.l #100,d1
 add.l d1,d0
 rts
 ENDC
