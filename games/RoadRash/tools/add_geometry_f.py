from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text().replace(' bsr.w f_hud_init',' bsr.w f_geometry_init\n bsr.w f_hud_init',1)
s+='''
; F2a prototype: one segment walk, four exact native DDAs, fused width/shift.
f_geometry_init:
 lea f_geometry_base(pc),a0
 move.l a5,(a0)
 move.l a5,a1
 adda.l #$75f2,a1
 lea f_geometry(pc),a0
 move.w #$4eb9,(a1)
 move.l a0,2(a1)
 move.l #$6000005e,6(a1) ; skip the original four edge passes and width pass
 rts
f_geometry_base: dc.l 0
f_geometry:
 lea -48(a7),a7
 move.l a7,a5
 move.l f_geometry_base(pc),a6
 adda.l #$27004,a6
 clr.w (a5)
 move.l $26a(a6),a0 ; $a726e
 move.w (a0),44(a5)
.segment:
 move.w (a5),d0
 move.w $66(a6,d0.w),d1
 move.w d1,4(a5)
 lea $103a(a6),a1
 move.w (a1,d0.w),d2
 sub.w d1,d2
 ble .next
 move.w d2,2(a5)
 move.w $64(a6,d0.w),d3
 sub.w d1,d3
 move.w d3,42(a5)
 cmpi.w #2,d3
 ble .slopes
 moveq #0,d6
 move.w d3,d4
.reduce:
 cmpi.w #$100,d4
 bmi .lookup
 lsr.w #1,d4
 addq.w #1,d6
 bra .reduce
.lookup:
 move.l f_geometry_base(pc),a1
 adda.l #$9b1e,a1
 add.w d4,d4
 move.w (a1,d4.w),d4
 lsr.w d6,d4
 move.w d4,6(a5)
.slopes:
 lea 8(a5),a2
 lea $12c(a6),a1
 bsr .slope
 lea $c8(a6),a1
 bsr .slope
 move.l a6,a1
 bsr .slope
 lea $190(a6),a1
 bsr .slope
 move.w 4(a5),d6
 move.w d6,d4
 add.w d4,d4
 lea $28a(a6),a0 ; $a728e
 adda.w d4,a0
 move.l f_geometry_base(pc),a3
 adda.l #$93dc,a3
 adda.w d4,a3
 lea $130(a3),a4 ; $8950c
 movem.l 24(a5),d0-d3
 move.w 2(a5),d7
 subq.w #1,d7
.line:
 swap d0
 swap d1
 swap d2
 swap d3
 move.w d0,$1c0(a0)
 move.w d1,(a0)
 move.w d2,$380(a0)
 move.w d3,$540(a0)
 cmp.w 44(a5),d6
 blt .advance
 cmpi.w #152,d6
 bge .advance
 move.w d3,d4
 sub.w d1,d4
 move.w d4,d5
 asr.w #1,d5
 add.w d5,d4
 lsr.w #6,d4
 bne .width
 moveq #1,d4
.width:
 move.w d2,d5
 addi.w #$200,d5
 cmpi.w #$140,d5
 blt .left
 moveq #0,d5
 moveq #0,d4
.left:
 tst.w d5
 bpl .store
 add.w d5,d4
 moveq #0,d5
 tst.w d4
 bpl .store
 moveq #0,d4
.store:
 move.w d5,(a3)
 move.w d4,(a4)
.advance:
 swap d0
 swap d1
 swap d2
 swap d3
 add.l 8(a5),d0
 add.l 12(a5),d1
 add.l 16(a5),d2
 add.l 20(a5),d3
 addq.w #1,d6
 addq.l #2,a0
 addq.l #2,a3
 addq.l #2,a4
 dbf d7,.line
.next:
 addq.w #2,(a5)
 cmpi.w #62,(a5)
 blt .segment
 move.l f_geometry_base(pc),a3
 adda.l #$93dc,a3
 lea $130(a3),a4
 move.w 44(a5),d0
 subq.w #1,d0
 moveq #0,d1
.clear:
 move.w d1,(a3)+
 move.w d1,(a4)+
 dbf d0,.clear
 lea 48(a7),a7
 rts
.slope:
 move.w 2(a1,d0.w),d4
 move.w (a1,d0.w),d5
 sub.w d4,d5
 swap d4
 clr.w d4
 move.l d4,16(a2)
 cmpi.w #2,d3
 bgt .multiply
 swap d5
 clr.w d5
 cmpi.w #2,d3
 bne .save
 asr.l #1,d5
 bra .save
.multiply:
 muls.w 6(a5),d5
.save:
 move.l d5,(a2)+
 rts
''';p.write_text(s)
