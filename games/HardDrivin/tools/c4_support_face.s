; A1: convex XYZ word vertices, D0: count (3..32), D1/D2: query X/Z.
; D0=1 iff finite upward-facing projected polygon covers query; otherwise0.
; Caller saves D3-D7/A2-A3. No plane extrapolation or arbitrary slope cutoff.
_private_support_face:
 cmpi.w #3,d0
 blo .outside
 cmpi.w #32,d0
 bhi .outside
 move.w d0,d7
 move.w d1,d3
 addi.w #8191,d3
 cmpi.w #16382,d3
 bhi .outside
 move.w d2,d3
 addi.w #8191,d3
 cmpi.w #16382,d3
 bhi .outside
 movea.l a1,a2
 subq.w #1,d0
.range:
 move.w (a2),d3
 addi.w #8191,d3
 cmpi.w #16382,d3
 bhi .outside
 move.w 4(a2),d3
 addi.w #8191,d3
 cmpi.w #16382,d3
 bhi .outside
 addq.w #6,a2
 dbf d0,.range
 movea.l a1,a2
 moveq #0,d0
.edge:
 lea 6(a2),a3
 cmpi.w #1,d7
 bne.s .next
 movea.l a1,a3
.next:
 move.w (a2),d3
 sub.w d1,d3
 move.w 4(a2),d4
 sub.w d2,d4
 move.w (a3),d5
 sub.w d1,d5
 move.w 4(a3),d6
 sub.w d2,d6
 muls.w d6,d3
 muls.w d5,d4
 sub.l d4,d3
 bgt.s .outside
 beq.s .zero
 moveq #1,d0
.zero:
 movea.l a3,a2
 subq.w #1,d7
 bne.s .edge
 rts
.outside:
 moveq #0,d0
 rts
