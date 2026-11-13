; Buffered prediction saves occupied slots and camera/scratch 61..63.
; Records are 120 bytes per slot. Empty slots are saved lazily, before the
; native allocator's first write, so render attachments restore stale bytes too.
timing_scene_save_active:
        lea     timing_scene_saved_mask(pc),a0
        moveq   #15,d0
.clear:
        clr.l   (a0)+
        dbra    d0,.clear
        lea     timing_scene_saved_count(pc),a0
        clr.w   (a0)
        moveq   #0,d4
.slot:
        cmpi.w  #61,d4
        bhs.s   .save
        tst.w   AX_1700(a4,d4.w*2)
        beq.s   .next
.save:
        move.w  d4,d0
        bsr.w   timing_scene_save_slot
.next:
        addq.w  #1,d4
        cmpi.w  #64,d4
        blo.s   .slot
        rts

; D0=slot, D4 preserved for caller. The mask also prevents attachment reuse
; from replacing the original backup with an already staged pose.
timing_scene_save_slot:
        lea     timing_scene_saved_mask(pc),a0
        tst.b   (a0,d0.w)
        bne.w   .done
        move.b  #1,(a0,d0.w)
        lea     timing_scene_saved_count(pc),a0
        move.w  (a0),d1
        addq.w  #1,(a0)
        lea     timing_scene_saved_slots(pc),a0
        move.b  d0,(a0,d1.w)
        lea     (a4,d0.w*2),a2
        lea     (a4,d0.w*4),a3
        lea     (a4,d0.w),a6
        move.w  d0,d1
        mulu.w  #12,d1
        lea     (a4,d1.w),a5
        mulu.w  #120,d0
        lea     timing_scene_saved(pc),a1
        adda.w  d0,a1
        move.l  AX_119c(a5),(a1)+
        move.l  AX_11a0(a5),(a1)+
        move.l  AX_11a4(a5),(a1)+
        move.l  AX_214a(a5),(a1)+
        move.l  AX_214e(a5),(a1)+
        move.l  AX_2152(a5),(a1)+
        move.l  AX_3452(a5),(a1)+
        move.l  AX_3456(a5),(a1)+
        move.l  AX_345a(a5),(a1)+
        move.l  AX_3752(a5),(a1)+
        move.l  AX_3756(a5),(a1)+
        move.l  AX_375a(a5),(a1)+
        move.l  AX_1d6e(a5),(a1)+
        move.l  AX_1d72(a5),(a1)+
        move.l  AX_1d76(a5),(a1)+
        move.w  AX_1700(a2),(a1)+
        move.w  AX_17f8(a2),(a1)+
        move.w  AX_14c8(a2),(a1)+
        move.w  AX_157a(a2),(a1)+
        move.w  AX_15fa(a2),(a1)+
        move.w  AX_167a(a2),(a1)+
        move.l  AX_2e6e(a3),(a1)+
        move.w  AX_1afc(a2),(a1)+
        move.w  AX_3e90(a2),(a1)+
        move.w  AX_33cc(a2),(a1)+
        move.w  AX_3fbc(a2),(a1)+
        move.w  AX_18c8(a2),(a1)+
        move.w  AX_2c6e(a2),(a1)+
        move.w  AX_2d6e(a2),(a1)+
        move.b  AX_3a6a(a6),(a1)+
        move.b  AX_3b46(a6),(a1)+
        move.w  AX_4078(a2),(a1)+
        move.w  AX_40f8(a2),(a1)+
        move.w  AX_2dee(a2),(a1)+
        move.w  AX_245e(a2),(a1)+
        move.w  AX_24de(a2),(a1)+
        move.w  AX_255e(a2),(a1)+
        move.w  AX_2bea(a2),(a1)+
        move.w  AX_2cee(a2),(a1)+
        move.l  AX_3b86(a5),(a1)+
        move.l  AX_3b8a(a5),(a1)+
        move.l  AX_3b8e(a5),(a1)+
.done:
        rts

timing_scene_restore_active:
        movem.l d3-d4/a3/a5-a6,-(sp)
        moveq   #0,d4
.slot:
        cmp.w   timing_scene_saved_count(pc),d4
        bhs.w   .done
        lea     timing_scene_saved_slots(pc),a0
        moveq   #0,d0
        move.b  (a0,d4.w),d0
        lea     (a4,d0.w*2),a2
        lea     (a4,d0.w*4),a3
        lea     (a4,d0.w),a6
        move.w  d0,d1
        mulu.w  #12,d1
        lea     (a4,d1.w),a5
        mulu.w  #120,d0
        lea     timing_scene_saved(pc),a1
        adda.w  d0,a1
        move.l  (a1)+,AX_119c(a5)
        move.l  (a1)+,AX_11a0(a5)
        move.l  (a1)+,AX_11a4(a5)
        move.l  (a1)+,AX_214a(a5)
        move.l  (a1)+,AX_214e(a5)
        move.l  (a1)+,AX_2152(a5)
        move.l  (a1)+,AX_3452(a5)
        move.l  (a1)+,AX_3456(a5)
        move.l  (a1)+,AX_345a(a5)
        move.l  (a1)+,AX_3752(a5)
        move.l  (a1)+,AX_3756(a5)
        move.l  (a1)+,AX_375a(a5)
        move.l  (a1)+,AX_1d6e(a5)
        move.l  (a1)+,AX_1d72(a5)
        move.l  (a1)+,AX_1d76(a5)
        move.w  (a1)+,AX_1700(a2)
        move.w  (a1)+,AX_17f8(a2)
        move.w  (a1)+,AX_14c8(a2)
        move.w  (a1)+,AX_157a(a2)
        move.w  (a1)+,AX_15fa(a2)
        move.w  (a1)+,AX_167a(a2)
        move.l  (a1)+,AX_2e6e(a3)
        move.w  (a1)+,AX_1afc(a2)
        move.w  (a1)+,AX_3e90(a2)
        move.w  (a1)+,AX_33cc(a2)
        move.w  (a1)+,AX_3fbc(a2)
        move.w  (a1)+,AX_18c8(a2)
        move.w  (a1)+,AX_2c6e(a2)
        move.w  (a1)+,AX_2d6e(a2)
        move.b  (a1)+,AX_3a6a(a6)
        move.b  (a1)+,AX_3b46(a6)
        move.w  (a1)+,AX_4078(a2)
        move.w  (a1)+,AX_40f8(a2)
        move.w  (a1)+,AX_2dee(a2)
        move.w  (a1)+,AX_245e(a2)
        move.w  (a1)+,AX_24de(a2)
        move.w  (a1)+,AX_255e(a2)
        move.w  (a1)+,AX_2bea(a2)
        move.w  (a1)+,AX_2cee(a2)
        move.l  (a1)+,AX_3b86(a5)
        move.l  (a1)+,AX_3b8a(a5)
        move.l  (a1)+,AX_3b8e(a5)
        addq.w  #1,d4
        bra.w   .slot
.done:
        movem.l (sp)+,d3-d4/a3/a5-a6
        rts

; E:2b648: selected native allocator slot is D2, before position/type writes.
; Replay the displaced operations and preserve every other register.
timing_scene_allocate:
        movem.l d0-d2/a0-a3/a5-a6,-(sp)
        tst.w   timing_scene_staged(pc)
        beq.s   .native
        move.w  d2,d0
        bsr.w   timing_scene_save_slot
.native:
        movem.l (sp)+,d0-d2/a0-a3/a5-a6
        move.l  timing_game(pc),-(sp)
        addi.l  #E_2b64e,(sp)
        move.w  d2,d0
        ext.l   d0
        add.l   d0,d0
        rts

        cnop 0,2
timing_scene_saved_count: dc.w 0
timing_scene_saved_mask: dcb.b 64,0
timing_scene_saved_slots: dcb.b 64,0
