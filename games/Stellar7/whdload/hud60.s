; Cockpit indicator animation: native four-pixel step every reference 200 ms,
; independent of presentation count. Data $1f5c/$1f5e retain native units/state.
        IFNE HUD_CLOCK
s60_hud_native: ds.b 50
s60_hud_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$c3ba,a0
        cmp.w #$3039,(a0)
        bne s60_bad
        cmp.l #$0c400084,(6,a0)
        bne s60_bad
        cmp.w #$6c0a,(10,a0)
        bne s60_bad
        cmp.l #$33fc0004,(12,a0)
        bne s60_bad
        cmp.l #$600e0c40,(20,a0)
        bne s60_bad
        cmp.l #$00b06f08,(24,a0)
        bne s60_bad
        cmp.l #$72fc33c1,(28,a0)
        bne s60_bad
        cmp.w #$3039,(36,a0)
        bne s60_bad
        cmp.w #$d179,(42,a0)
        bne s60_bad
        cmp.w #$3039,(48,a0)
        bne s60_bad
        move.l ($2af8,a1),d0 ; relocated active flag is data+$1e53
        add.l #$1f5c-$1e53,d0
        cmp.l (2,a0),d0
        bne s60_bad
        cmp.l (44,a0),d0
        bne s60_bad
        cmp.l (50,a0),d0
        bne s60_bad
        addq.l #2,d0
        cmp.l (16,a0),d0
        bne s60_bad
        cmp.l (32,a0),d0
        bne s60_bad
        cmp.l (38,a0),d0
        bne s60_bad
        lea (s60_hud_native,pc),a3
        moveq #11,d0
.copy:  move.l (a0)+,(a3)+ ; all native branches remain within these 48 bytes
        dbf d0,.copy
        move.w #$4e75,(a3)
        lea (s60_hud_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_hud_patches:
        PL_START
        PL_P $c3ba,s60_hud_draw ; entire six-byte MOVE.W, no interior entry
        PL_END
s60_hud_draw:
        bra.w s60_hud_draw_entry
        dc.b 'HU60'
s60_hud_state: dc.l 0
        dc.w 0 ; valid; reset at each gameplay session or while hidden
s60_hud_draw_entry: move.w (s60_running,pc),d0
        IFD VERIFY
        IFD HUD_BAD_RENDER
        ; Negative control: the fixture must detect render-driven advancement.
        ELSE
        bne .draw
        ENDC
        ELSE
        bne .draw
        ENDC
        bsr s60_hud_native ; inactive callers preserve native behavior
.draw:  S60_TAIL $c3ea
s60_hud_reset:
        lea (s60_hud_state,pc),a0
        clr.l (a0)+
        clr.w (a0)
        rts
s60_hud_update:
        movem.l d0-d1/a0,-(sp)
        move.w (s60_running,pc),d0
        beq .done
        move.w (s60_rendering,pc),d0
        bne .done
        cmp.w #50,($1e72-S60_DATA,a4)
        ble .reset
        lea (s60_hud_state,pc),a0
        tst.w (4,a0)
        beq .due
        move.l (s60_ticks,pc),d0
        sub.l (a0),d0
        cmp.l #S60_LEGACY_DIV,d0
        bcs .done
.due:   move.l (s60_ticks,pc),(a0)
        move.w #1,(4,a0)
        bsr s60_hud_native
        bra .done
.reset: bsr s60_hud_reset
.done:  movem.l (sp)+,d0-d1/a0
        rts
        ENDC
