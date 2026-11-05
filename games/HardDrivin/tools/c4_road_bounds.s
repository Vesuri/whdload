; A1 points at three native car-space road cross-sections (six XYZ vertices).
; D2 mask: bit1 permits first quad, bit0 permits second quad.
; Return D0=1 only when origin is in a nondegenerate convex projected quad.
; Bound coordinates before signed products; uncertain/far geometry is rejected.
_private_road_bounds:
 moveq #5,d7
 movea.l a1,a2
.check_range:
 move.w (a2),d0
 addi.w #8191,d0
 cmpi.w #16382,d0
 bhi .outside
 move.w 4(a2),d0
 addi.w #8191,d0
 cmpi.w #16382,d0
 bhi .outside
 addq.w #6,a2
 dbf d7,.check_range
 lea _private_road_indices(pc),a0
 moveq #1,d7
.quad:
 btst d7,d2
 bne.s .enabled
 addq.w #5,a0
 dbf d7,.quad
 bra .outside
.enabled:
 moveq #0,d5
 moveq #3,d6
.edge:
 moveq #0,d1
 move.b (a0)+,d1
 lea (a1,d1.w),a2
 moveq #0,d1
 move.b (a0),d1
 lea (a1,d1.w),a3
 move.w (a2),d3
 muls.w 4(a3),d3
 move.w 4(a2),d4
 muls.w (a3),d4
 sub.l d4,d3
 beq.s .next_edge
 moveq #1,d4
 tst.l d3
 bpl.s .sign
 moveq #-1,d4
.sign:
 tst.w d5
 beq.s .first_sign
 cmp.w d4,d5
 bne.s .next_quad
.first_sign:
 move.w d4,d5
.next_edge:
 dbf d6,.edge
 tst.w d5
 bne.s .inside
 moveq #0,d6
 bra.s .next_quad
.inside:
 moveq #1,d0
 rts
.next_quad:
 ; The next list starts five bytes after this quad's start.
 adda.w d6,a0
 addq.w #1,a0
 dbf d7,.quad
.outside:
 moveq #0,d0
 rts
_private_road_indices: dc.b 0,6,18,12,0,12,18,30,24,12
 even
