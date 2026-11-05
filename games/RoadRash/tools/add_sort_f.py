from pathlib import Path
p=Path('src/cpu_work.s');s=p.read_text().replace(' bsr.w f_dispatch_init',' bsr.w f_sort_init\n bsr.w f_dispatch_init',1)
s+='''
; F5c: temporal permutation seed, stable ties retain incoming draw-list order.
; Count changes reset to ordinal order; identities need not persist between lists.
f_sort_init:
 move.l a5,a1
 adda.l #$b37e,a1
 lea f_sort_native(pc),a0
 move.l (a1),(a0)
 move.w 4(a1),4(a0)
 move.l a5,d0
 addi.l #$b384,d0
 move.l d0,8(a0)
 lea f_sort(pc),a0
 move.w #$4ef9,(a1)
 move.l a0,2(a1)
 rts
f_sort_native:
 movem.l d0-d7/a0-a7,-(a7)
 move.l (a0)+,(a1)
 jmp $0
f_sort_count: dc.w 0
f_sort_order: ds.w 64
f_sort:
 movem.l d0-d7/a0-a6,-(a7)
 move.l a0,a3
 moveq #0,d7
.count:
 cmpi.w #-1,2(a3)
 beq .counted
 addq.l #4,a3
 addq.w #1,d7
 cmpi.w #64,d7
 bcs .count
 bra .native
.counted:
 cmpi.w #2,d7
 bcs .native
 lea f_sort_count(pc),a3
 cmp.w (a3),d7
 beq .seeded
 move.w d7,(a3)+
 moveq #0,d0
.reset:
 move.w d0,(a3)+
 addq.w #1,d0
 cmp.w d7,d0
 bcs .reset
.seeded:
 lea f_sort_order(pc),a3
 add.w d7,d7
 moveq #2,d4
.insert:
 move.w (a3,d4.w),d0
 move.w d0,d1
 lsl.w #2,d1
 move.l (a0,d1.w),d2
 lea (a3,d4.w),a4
 move.w d4,d5
 lsr.w #1,d5
 subq.w #1,d5
.scan:
 move.w -2(a4),d3
 move.w d3,d6
 lsl.w #2,d6
 cmp.l (a0,d6.w),d2
 bmi .shift
 bne .put
 cmp.w d3,d0
 bcc .put
.shift:
 move.w d3,(a4)
 subq.l #2,a4
 dbf d5,.scan
.put:
 move.w d0,(a4)
 addq.w #2,d4
 cmp.w d7,d4
 bcs .insert
 lsr.w #1,d7
 subq.w #1,d7
.publish:
 move.w (a3)+,d0
 move.w d0,(a2)+
 lsl.w #2,d0
 move.l (a0,d0.w),(a1)+
 dbf d7,.publish
 move.l #-1,(a1)
 move.w #-1,(a2)
 movem.l (a7)+,d0-d7/a0-a6
 rts
.native:
 movem.l (a7)+,d0-d7/a0-a6
 bra f_sort_native
''';p.write_text(s)
