; Native depth sort is unstable for ties. A ship's model-49 death explosion
; starts at its parent's position; rounded depths alternate between equal and
; one unit apart. Keep the parent before its explosion only within a depth tie.
; Change the completed draw list, never geometry, effect scripts or world state.
effect_order:
        movem.l d0-d3/a0-a3,-(sp)
        tst.w   intro_active(pc)
        beq.w   .done
        lea     EFFECT_LIST(a4),a0
.next:
        move.w  (a0)+,d0         ; native list contains doubled slot indices
        bmi.w   .done
        lea     EFFECT_CLASS(a4),a1
        cmpi.w  #5,(a1,d0.w)
        bne.s   .next
        lea     EFFECT_MODEL(a4),a1
        cmpi.w  #49,(a1,d0.w)
        bne.s   .next
        move.w  d0,d1
        lsr.w   #1,d1
        lea     EFFECT_OWNER(a4),a1
        moveq   #0,d2
        move.b  (a1,d1.w),d2
        cmpi.w  #10,d2
        bhs.s   .next
        add.w   d2,d2
        lea     EFFECT_CLASS(a4),a1
        cmpi.w  #12,(a1,d2.w)
        bne.s   .next
        lea     EFFECT_DEPTH(a4),a1
        move.w  (a1,d0.w),d3
        cmp.w   (a1,d2.w),d3
        bne.s   .next
        movea.l a0,a2
.find:
        move.w  (a2)+,d1
        bmi.s   .next           ; absent or already drawn parent: leave alone
        cmp.w   d1,d2
        bne.s   .find
        subq.l  #2,a2
        movea.l a2,a3
.shift:
        move.w  -(a3),(a2)
        movea.l a3,a2
        cmpa.l  a0,a3
        bhs.s   .shift
        move.w  d2,(a2)
        addq.l  #2,a0           ; skip the explosion just moved one place
        bra.s   .next
.done:
        movem.l (sp)+,d0-d3/a0-a3
        rts
