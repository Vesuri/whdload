; Private prototype: replace rendered-object infinite plane with finite faces.
; Entry still gated by native E94B; world scan covers active main-pool surfaces.
; Not final overhead-surface, extra-pool, timing or performance policy.
_private_object_ground:
 movem.l d0-d7/a0-a6,-(a7)
 movea.l _phase_steering_body(pc),a0
 adda.l #$c94e-$b398,a0
 jsr (a0)
 lea _private_object_saved(pc),a0
 lea -$16ca(a4),a1
 moveq #3,d0
.save_render:
 move.l (a1)+,(a0)+
 dbf d0,.save_render
 lea -$66bc(a4),a1
 moveq #2,d0
.save_angles:
 move.w (a1)+,(a0)+
 dbf d0,.save_angles
 lea -$16b2(a4),a1
 moveq #8,d0
.save_plane:
 move.w (a1)+,(a0)+
 dbf d0,.save_plane
 lea -$6bb8(a4),a0
 lea -$16c6(a4),a1
 moveq #5,d0
.trig:
 move.w (a0)+,(a1)+
 dbf d0,.trig
 lea -$66b6(a4),a0
 lea -$66bc(a4),a1
 moveq #2,d0
.angles:
 move.w (a0)+,(a1)+
 dbf d0,.angles
 movea.l -$669e(a4),a3
 move.w -$669a(a4),d7
 beq .restore
 subq.w #1,d7
.object:
 tst.b 30(a3)
 beq.s .next
 move.b 28(a3),d0
 andi.b #$12,d0
 beq.s .next
 ; Native radius (model bound+60) plus one wheel's XZ reach.
 moveq #0,d2
 move.w 6(a3),d2
 addi.l #75,d2
 moveq #2,d6
 lea 8(a3),a0
 lea -$670a(a4),a1
.near:
 move.w (a0)+,d0
 ext.l d0
 move.w (a1)+,d1
 ext.l d1
 sub.l d1,d0
 bpl.s .positive
 neg.l d0
.positive:
 cmp.l d2,d0
 bgt.s .next
 dbf d6,.near
 movem.l d7/a3,-(a7)
 bsr _private_object_one
 movem.l (a7)+,d7/a3
.next:
 adda.w #56,a3
 dbf d7,.object
.restore:
 lea _private_object_saved(pc),a0
 lea -$16ca(a4),a1
 moveq #3,d0
.render:
 move.l (a0)+,(a1)+
 dbf d0,.render
 lea -$66bc(a4),a1
 moveq #2,d0
.old_angles:
 move.w (a0)+,(a1)+
 dbf d0,.old_angles
 lea -$16b2(a4),a1
 moveq #8,d0
.old_plane:
 move.w (a0)+,(a1)+
 dbf d0,.old_plane
 movem.l (a7)+,d0-d7/a0-a6
 rts
_private_object_one:
 moveq #0,d0
 move.w 20(a3),d0
 beq .done
 moveq #0,d1
 move.b 22(a3),d1
 add.l d1,d0
 cmpi.l #256,d0
 bhi .done
 lea _private_object_clone(pc),a0
 movea.l a3,a1
 moveq #13,d0
.copy:
 move.l (a1)+,(a0)+
 dbf d0,.copy
 lea _private_object_clone(pc),a0
 lea -$670a(a4),a1
 moveq #2,d0
.translate:
 move.w 8(a0),d1
 sub.w (a1)+,d1
 move.w d1,(a0)+
 dbf d0,.translate
 lea _private_object_vertices(pc),a0
 move.l a0,-$16ca(a4)
 pea _private_object_clone(pc)
 movea.l _phase_steering_body(pc),a0
 adda.l #$97dc-$b398,a0
 jsr (a0)
 addq.w #4,a7
 lea _private_object_clone(pc),a0
 movea.l 52(a0),a2
 moveq #0,d7
 move.b 23(a0),d7
 beq .done
 subq.w #1,d7
.face:
 moveq #0,d6
 move.b (a2)+,d6
 addq.w #1,a2
 movea.l a2,a0
 adda.w d6,a2
 addq.w #1,a2
 cmpi.w #3,d6
 blo.s .next
 cmpi.w #32,d6
 bhi.s .next
 lea _private_object_face(pc),a1
 move.w d6,d5
 subq.w #1,d5
.vertex:
 moveq #0,d0
 move.b (a0)+,d0
 lea _private_object_clone(pc),a3
 cmp.w 20(a3),d0
 bhs.s .next
 mulu.w #6,d0
 lea _private_object_vertices(pc),a3
 adda.l d0,a3
 move.l (a3)+,(a1)+
 move.w (a3),(a1)+
 dbf d5,.vertex
 movem.l d7/a2,-(a7)
 bsr _private_object_face_wheels
 movem.l (a7)+,d7/a2
.next:
 dbf d7,.face
.done:
 rts
_private_object_face_wheels:
 ; Plane solver consumes the original first three vertices, never clipped ones.
 lea _private_object_face(pc),a0
 lea -$16b2(a4),a1
 moveq #8,d0
.plane:
 move.w (a0)+,(a1)+
 dbf d0,.plane
 lea -$7354(a4),a3
 lea -$6b82(a4),a2
 moveq #3,d7
.wheel:
 movem.l d6-d7/a2-a3,-(a7)
 move.w d6,d0
 move.w (a3),d1
 move.w 4(a3),d2
 lea _private_object_face(pc),a1
 bsr _private_support_face
 movem.l (a7)+,d6-d7/a2-a3
 tst.w d0
 beq.s .next
 movem.l d6-d7/a2-a3,-(a7)
 move.w 4(a3),-(a7)
 move.w 2(a3),-(a7)
 move.w (a3),-(a7)
 movea.l _phase_steering_body(pc),a0
 adda.l #$c6ec-$b398,a0
 jsr (a0)
 addq.w #6,a7
 movem.l (a7)+,d6-d7/a2-a3
 cmp.w (a2),d0
 bge.s .next
 move.w d0,(a2)
.next:
 addq.w #6,a3
 addq.w #2,a2
 dbf d7,.wheel
 rts
_private_object_saved: ds.b 40
_private_object_clone: ds.b 56
_private_object_face: ds.b 32*6
_private_object_vertices: ds.b 256*6
 even
