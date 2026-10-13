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
        tst.w   $1700(a4,d4.w*2)
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
        move.l  $119c(a5),(a1)+
        move.l  $11a0(a5),(a1)+
        move.l  $11a4(a5),(a1)+
        move.l  $214a(a5),(a1)+
        move.l  $214e(a5),(a1)+
        move.l  $2152(a5),(a1)+
        move.l  $3452(a5),(a1)+
        move.l  $3456(a5),(a1)+
        move.l  $345a(a5),(a1)+
        move.l  $3752(a5),(a1)+
        move.l  $3756(a5),(a1)+
        move.l  $375a(a5),(a1)+
        move.l  $1d6e(a5),(a1)+
        move.l  $1d72(a5),(a1)+
        move.l  $1d76(a5),(a1)+
        move.w  $1700(a2),(a1)+
        move.w  $17f8(a2),(a1)+
        move.w  $14c8(a2),(a1)+
        move.w  $157a(a2),(a1)+
        move.w  $15fa(a2),(a1)+
        move.w  $167a(a2),(a1)+
        move.l  $2e6e(a3),(a1)+
        move.w  $1afc(a2),(a1)+
        move.w  $3e90(a2),(a1)+
        move.w  $33cc(a2),(a1)+
        move.w  $3fbc(a2),(a1)+
        move.w  $18c8(a2),(a1)+
        move.w  $2c6e(a2),(a1)+
        move.w  $2d6e(a2),(a1)+
        move.b  $3a6a(a6),(a1)+
        move.b  $3b46(a6),(a1)+
        move.w  $4078(a2),(a1)+
        move.w  $40f8(a2),(a1)+
        move.w  $2dee(a2),(a1)+
        move.w  $245e(a2),(a1)+
        move.w  $24de(a2),(a1)+
        move.w  $255e(a2),(a1)+
        move.w  $2bea(a2),(a1)+
        move.w  $2cee(a2),(a1)+
        move.l  $3b86(a5),(a1)+
        move.l  $3b8a(a5),(a1)+
        move.l  $3b8e(a5),(a1)+
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
        move.l  (a1)+,$119c(a5)
        move.l  (a1)+,$11a0(a5)
        move.l  (a1)+,$11a4(a5)
        move.l  (a1)+,$214a(a5)
        move.l  (a1)+,$214e(a5)
        move.l  (a1)+,$2152(a5)
        move.l  (a1)+,$3452(a5)
        move.l  (a1)+,$3456(a5)
        move.l  (a1)+,$345a(a5)
        move.l  (a1)+,$3752(a5)
        move.l  (a1)+,$3756(a5)
        move.l  (a1)+,$375a(a5)
        move.l  (a1)+,$1d6e(a5)
        move.l  (a1)+,$1d72(a5)
        move.l  (a1)+,$1d76(a5)
        move.w  (a1)+,$1700(a2)
        move.w  (a1)+,$17f8(a2)
        move.w  (a1)+,$14c8(a2)
        move.w  (a1)+,$157a(a2)
        move.w  (a1)+,$15fa(a2)
        move.w  (a1)+,$167a(a2)
        move.l  (a1)+,$2e6e(a3)
        move.w  (a1)+,$1afc(a2)
        move.w  (a1)+,$3e90(a2)
        move.w  (a1)+,$33cc(a2)
        move.w  (a1)+,$3fbc(a2)
        move.w  (a1)+,$18c8(a2)
        move.w  (a1)+,$2c6e(a2)
        move.w  (a1)+,$2d6e(a2)
        move.b  (a1)+,$3a6a(a6)
        move.b  (a1)+,$3b46(a6)
        move.w  (a1)+,$4078(a2)
        move.w  (a1)+,$40f8(a2)
        move.w  (a1)+,$2dee(a2)
        move.w  (a1)+,$245e(a2)
        move.w  (a1)+,$24de(a2)
        move.w  (a1)+,$255e(a2)
        move.w  (a1)+,$2bea(a2)
        move.w  (a1)+,$2cee(a2)
        move.l  (a1)+,$3b86(a5)
        move.l  (a1)+,$3b8a(a5)
        move.l  (a1)+,$3b8e(a5)
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
        addi.l  #$2b64e,(sp)
        move.w  d2,d0
        ext.l   d0
        add.l   d0,d0
        rts

        cnop 0,2
timing_scene_saved_count: dc.w 0
timing_scene_saved_mask: dcb.b 64,0
timing_scene_saved_slots: dcb.b 64,0
