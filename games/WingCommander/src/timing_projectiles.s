; Successful weapon constructors certify a fully initialized presentation pose.
; Pending identities last only until the post-world snapshot. No game data writes.
; These hooks run after native construction, shared by player and AI callers.
projectile_gun_return:              ; E:c912 -> native C458 epilogue
        movem.l d0-d3/a0-a1,-(sp)
        move.w  d2,d0
        bsr.w   projectile_created
        movem.l (sp)+,d0-d3/a0-a1
        move.w  d2,d0
        movem.l (sp)+,d2-d7/a2-a3
        unlk    a5
        rts
projectile_effect_return:           ; E:c316 -> native C1E4 epilogue
        movem.l d0-d3/a0-a1,-(sp)
        move.w  d2,d0
        bsr.w   projectile_created
        movem.l (sp)+,d0-d3/a0-a1
        move.w  d2,d0
        movem.l (sp)+,d2-d7/a2
        unlk    a5
        rts
projectile_missile_return:          ; E:ca5e -> native CA38 epilogue
        movem.l d0-d3/a0-a1,-(sp)
        move.w  ccr,-(sp)
        moveq   #-1,d3             ; this constructor does not reload gun cooldown
        bsr.w   projectile_created
        move.w  (sp)+,ccr
        movem.l (sp)+,d0-d3/a0-a1
        movem.l (sp)+,d2-d5
        rts
projectile_init_return:             ; E:9a52: any slot reinitialization revokes birth
        movem.l d0/a0,-(sp)
        tst.w   timing_scene_staged(pc)
        bne.s   .done
        cmpi.w  #60,d2
        bhi.s   .done               ; includes -1 allocation failure
        lea     field_shot_targets(pc),a0
        move.b  #-1,(a0,d2.w)
        lea     field_shot_effects(pc),a0
        clr.b   (a0,d2.w)
        lea     projectile_types(pc),a0
        clr.w   (a0,d2.w*2)
        lea     projectile_cooldown_valid(pc),a0
        clr.b   (a0,d2.w)
.done:
        movem.l (sp)+,d0/a0
        move.w  d2,d0
        movem.l (sp)+,d2
        rts

; D0.w created slot, D3.w shooter or -1. Scratch D0-D3/A0-A1 only.
projectile_created:
        tst.w   timing_active(pc)
        beq.w   .done
        tst.w   timing_scene_staged(pc)
        bne.w   .done
        cmpi.w  #60,d0
        bhi.w   .done
        lea     A_5888(a4),a0
        move.w  (a0,d0.w*2),d1
        cmpi.w  #5,d1              ; native approximate AI shot (model 48)
        beq.s   .record
        cmpi.w  #8,d1              ; cannon bolt
        beq.s   .record
        cmpi.w  #10,d1             ; missile constructor CA38
        beq.s   .record
        cmpi.w  #11,d1             ; launched guided projectile
        bne.s   .done
.record:
        lea     projectile_types(pc),a0
        move.w  d1,(a0,d0.w*2)
        lea     A_6136(a4),a0
        move.w  (a0,d0.w*2),d1
        lea     projectile_models(pc),a0
        move.w  d1,(a0,d0.w*2)
        cmpi.w  #9,d3
        bhi.s   .done
        lea     A_5888(a4),a0
        cmpi.w  #11,(a0,d3.w*2)
        blo.s   .done
        lea     A_5320(a4),a0
        move.w  (a0,d3.w*2),d1
        bmi.s   .done
        lea     projectile_cooldown(pc),a0
        move.w  d1,(a0,d3.w*2)
        lea     projectile_cooldown_valid(pc),a0
        move.b  #1,(a0,d3.w)
.done:
        rts

; Called at every snapshot and clock rebase; records never bridge modal cuts.
projectile_reset:
        movem.l d0/a0,-(sp)
        lea     projectile_types(pc),a0
        moveq   #31,d0
.types:
        clr.l   (a0)+
        dbf     d0,.types
        lea     projectile_cooldown_valid(pc),a0
        moveq   #15,d0
.cooldowns:
        clr.l   (a0)+
        dbf     d0,.cooldowns
        movem.l (sp)+,d0/a0
        rts
        cnop    0,4
projectile_types: dcb.w 64,0
projectile_models: dcb.w 64,0
projectile_cooldown: dcb.w 64,0
projectile_cooldown_valid: dcb.b 64,0
