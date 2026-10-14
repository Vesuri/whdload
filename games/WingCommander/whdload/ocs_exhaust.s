; O:2837a destructively converts mount offsets to screen coordinates. Retain
; its inputs once per world tick, after allocation, before native placement.
; No extra allocations, image selection, animation or RNG calls during drawing.
ocs_exhaust_capture:
        movem.l d0-d4/a0-a3,-(sp)
        lea ocs_exhaust_mounts(pc),a2
        moveq #10,d2
.slot:
        move.w #-1,(a2)
        move.w d2,d3
        add.w d3,d3
        lea (a4,d3.w),a3
        cmpi.w #7,$0e8e(a3)
        bne.w .next
        move.w $0f86(a3),d0
        cmpi.w #55,d0
        beq.s .mount
        cmpi.w #27,d0
        bne.w .next
.mount:
        moveq #0,d4
        move.b $3058(a4,d2.w),d4
        cmpi.w #10,d4
        bhs.w .next
        move.w d4,(a2)
        move.w d0,2(a2)
        move.w $20f8(a3),4(a2)
        move.w $2178(a3),6(a2)
        move.w $252e(a3),8(a2)
        add.w d4,d4
        lea (a4,d4.w),a0
        move.w $22fc(a3),d0
        sub.w $22fc(a0),d0
        ; Invert the native mount-angle mirroring, then apply the current
        ; parent's mirroring and rotation again at render time.
        move.w $21fc(a0),d1
        btst #5,d1
        beq.s .x
        neg.w d0
.x:
        btst #4,d1
        beq.s .angle
        neg.w d0
        addi.w #180,d0
.angle:
        move.w d0,10(a2)
.next:
        lea 12(a2),a2
        addq.w #1,d2
        cmpi.w #61,d2
        blo.w .slot
        lea ocs_exhaust_valid(pc),a0
        move.w #1,(a0)
        movem.l (sp)+,d0-d4/a0-a3
        rts

ocs_exhaust_draw:
        tst.w ocs_exhaust_valid(pc)
        beq.w .done
        movem.l d0-d4/a0-a3,-(sp)
        lea ocs_exhaust_mounts(pc),a2
        moveq #10,d2
.slot:
        move.w (a2),d4
        bmi.w .next
        move.w d2,d3
        add.w d3,d3
        lea (a4,d3.w),a3
        cmpi.w #7,$0e8e(a3)
        bne.w .next
        move.w 2(a2),d0
        cmp.w $0f86(a3),d0
        bne.w .next
        cmp.b $3058(a4,d2.w),d4
        bne.w .next
        move.w 4(a2),$20f8(a3)
        move.w 6(a2),$2178(a3)
        move.w 8(a2),$252e(a3)
        move.w 10(a2),-(sp)
        move.w d4,-(sp)
        jsr OCS_MOUNT_ANGLE
        addq.l #4,sp
        move.w d0,$22fc(a3)
        add.w d4,d4
        lea (a4,d4.w),a0
        cmpi.w #$8001,$20f8(a0)
        bne.s .next
        ; Native placement skips invisible parents. Hide the staged child too.
        move.w #$8001,$20f8(a3)
.next:
        lea 12(a2),a2
        addq.w #1,d2
        cmpi.w #61,d2
        blo.w .slot
        jsr OCS_ATTACHMENTS
        movem.l (sp)+,d0-d4/a0-a3
.done:
        rts
        cnop 0,2
ocs_exhaust_valid: dc.w 0
ocs_exhaust_mounts: dcb.b 51*12,0
