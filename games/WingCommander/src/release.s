; Translate public language/pacing options once before language selection.
; Internal CUSTOM1=3 is enhanced; 0/1 are Psygore's English/German. German
; keeps 1 until Psygore's loader has chosen wing.german (S:142a), so the
; converter setup sees 3 only for its call; release_patchseg then maps German
; to 3 or 0. German first rewrites the enhanced code's English game addresses.
release_setcpu:
        movem.l d0-d2/a0-a1,-(sp)
        lea     slave+$1de4(pc),a0
        lea     slave+$1e04(pc),a1
        move.l  (a0),d2
        cmpi.l  #1,d2
        bhi.s   .bad
        move.l  (a1),d2
        cmpi.l  #4,d2
        bhi.s   .bad
        tst.l   (a0)
        beq.s   .language
        bsr.w   release_german_install
        lea     release_german(pc),a0
        move.w  #1,(a0)
        lea     slave+$1de4(pc),a0
.language:
        tst.l   d2
        beq.s   .enhanced
        subq.l  #1,(a1)          ; public 1..4 -> Psygore 0..3
        bra.s   .ready
.enhanced:
        tst.l   (a0)
        beq.s   .english
        lea     release_german(pc),a0
        move.w  #2,(a0)
        lea     slave+$1de4(pc),a0
.english:
        move.l  #3,(a0)
.ready:
        movem.l (sp)+,d0-d2/a0-a1
        bsr.l   render_setcpu
        move.l  a0,-(sp)
        cmpi.w  #2,release_german(pc)
        bne.s   .done
        lea     slave+$1de4(pc),a0
        move.l  #1,(a0)          ; Psygore's loader takes wing.german
.done:
        move.l  (sp)+,a0
        rts
.bad:
        movem.l (sp)+,d0-d2/a0-a1
        bra.w   timing_bad

; The build assembles the enhanced code a second time with German game
; addresses (german_map.py) and lists every differing word here as slave
; offset and German word. Rewrite them once, before any of it runs.
release_german_install:
        movem.l d0/a0-a1,-(sp)
        lea     .anchor(pc),a0
.anchor:
        adda.l  #german_fixups-.anchor,a0
        lea     slave(pc),a1
.next:
        moveq   #0,d0
        move.w  (a0)+,d0
        beq.s   .flush
        move.w  (a0)+,(a1,d0.l)
        bra.s   .next
.flush:
        jsr     32(a2)           ; resload_FlushCache
        movem.l (sp)+,d0/a0-a1
        rts

release_german:  dc.w 0          ; 1 German Psygore's modes, 2 German enhanced

; Full enhanced converter gate, including flight allocation fallback.
; Flight and the clocked world intro have no limiter; other scenes keep normal.
release_limit:
        tst.w   timing_active(pc)
        bne.l   release_convert_wait
        tst.w   intro_active(pc)
        bne.l   release_convert_wait
.nonflight:
        bsr.w   slave+$17b8
        rts

; Fixes applied in every mode by a second list after Psygore's:
; - Bunk save. His NV storage is files: StoreNV returned 1 (failure) after a
;   successful resload_SaveFile and GetNVList returned without filling its
;   presence array, so the game cleared a saved bunk until the next reload.
;   Return success, list the existing Bed_N files and restore the
;   save-failure branch he NOPed.
; - TrainSim keys 1-4 (game bug). The fly-off animation is passed the pointer
;   choice d4, still -1 after a key; pass the stored choice (a2) instead.
; - Mouse (mouse.s). The room pointer follows port-0 mouse motion, and the left
;   button is port-1 fire, so it also clicks hotspots and skips what fire skips.
;   Each screen's pad reset arms a release guard that swallowed the first fire
;   click after it; it now arms only while a fire button is held.
; - Mouse in name entry. The TrainSim top-score name entry moves a selection
;   box over a character grid by stick edges; whole cells of mouse motion now
;   move it too.
; German now runs the English paths with German addresses: enhanced as 3 and
; Psygore's modes as 0, which adds only the waypoint marker order.
release_patchseg:
        movem.l d0/a0,-(sp)
        move.w  release_german(pc),d0
        beq.s   .language
        lea     slave+$1de4(pc),a0
        clr.l   (a0)
        subq.w  #1,d0
        beq.s   .language
        move.l  #3,(a0)
.language:
        movem.l (sp)+,d0/a0
        bsr.w   timing_patchseg
        movem.l d0-d1/a0-a1,-(sp)
        lea     fix_patch_en(pc),a0
        lea     mouse_params_en(pc),a1
        tst.w   release_german(pc)
        beq.s   .english
        lea     fix_patch_de(pc),a0
        lea     mouse_params_de(pc),a1
.english:
        move.l  a1,-(sp)
        movea.l d7,a1
        jsr     116(a2)          ; resload_PatchSeg
        movea.l (sp)+,a0
        move.l  d7,d0
        lsl.l   #2,d0
        addq.l  #4,d0
        bsr.w   mouse_init
        move.l  d7,d0
        lsl.l   #2,d0
        addq.l  #4,d0
        add.l   NAME_STEP(a0),d0
        lea     name_step(pc),a1
        move.l  d0,(a1)
        movem.l (sp)+,d0-d1/a0-a1
        rts

; Port-1 pad read in the VBL server (Psygore's S:1c2e); the left mouse button
; (CIA-A PRA bit 6) adds the red button, which the game decodes as fire.
mouse_pad:
        bsr.w   slave+$1c2e
        lea     mouse_fields(pc),a0     ; a0 is reloaded after this call
        addq.w  #1,(a0)
        btst    #6,$bfe001
        bne.s   .up
        bset    #22,d0
.up:
        rts

; Pad record reset (a0 = record): the click counter -1 ignores the next
; release. Keep it only for a red button or left mouse button held now.
mouse_guard:
        move.w  #-1,18(a0)
        btst    #7,$bfe001
        beq.s   .held
        btst    #6,$bfe001
        beq.s   .held
        clr.w   18(a0)
.held:
        rts

; Name entry grid poll (E:16ed0, G:16f6e): replaces move.w d0,-(sp) and
; jsr step(pc), with d0 = the stick's column step and the row step already
; pushed. Adds whole cells of mouse motion since the last poll. Columns stop
; at the grid edge (the stick wraps) and motion from other screens is dropped.
; Enters the native step with both arguments pushed, as the native call does.
NAME_SEL = 12                   ; parameter table: A4 offset, selected cell code
NAME_COLS = 14                  ; A4 offset, grid columns
NAME_STEP = 16                  ; H0 offset, native step (column, row)
NAME_CELL = 18                  ; mouse counts per cell (cells are 9 pixels)
mouse_name:
        subq.l  #2,sp
        move.l  2(sp),(sp)              ; return address below the column word
        move.w  d0,4(sp)
        movem.l d1-d4/a0-a1,-(sp)       ; column at 28(sp), row at 30(sp)
        movea.l mouse_params(pc),a1
        move.w  MP_SLOT(a1),d1
        lea     mouse_event(pc),a0
        move.l  a0,(a4,d1.w)
        move.w  NAME_SEL(a1),d3
        move.w  (a4,d3.w),d3
        move.w  NAME_COLS(a1),d4
        move.w  (a4,d4.w),d4
        lea     mouse_sum_x(pc),a0
        lea     name_used(pc),a1        ; used x, used y, last poll field
        move.w  mouse_fields(pc),d1
        move.w  d1,d2
        sub.w   4(a1),d2
        move.w  d1,4(a1)
        cmpi.w  #8,d2
        bls.s   .fresh
        move.w  (a0),(a1)               ; first poll on this screen
        move.w  2(a0),2(a1)
        bra.s   .done
.fresh:
        move.w  (a0),d1
        sub.w   (a1),d1
        ext.l   d1
        divs.w  #NAME_CELL,d1           ; whole cells, toward zero
        subi.w  #32,d3
        ext.l   d3
        divs.w  d4,d3
        swap    d3                      ; column
        move.w  d3,d2
        neg.w   d2                      ; lowest step
        cmp.w   d2,d1
        blt.s   .edge
        move.w  d4,d2
        subq.w  #1,d2
        sub.w   d3,d2                   ; highest step
        cmp.w   d2,d1
        bgt.s   .edge
        move.w  d1,d2
        muls.w  #NAME_CELL,d2
        add.w   d2,(a1)
        bra.s   .column
.edge:
        move.w  d2,d1
        move.w  (a0),(a1)               ; at the edge: drop the remainder
.column:
        add.w   d1,28(sp)
        move.w  2(a0),d1
        sub.w   2(a1),d1
        ext.l   d1
        divs.w  #NAME_CELL,d1
        move.w  d1,d2
        muls.w  #NAME_CELL,d2
        add.w   d2,2(a1)
        add.w   d1,30(sp)               ; the native step clamps rows
.done:
        movem.l (sp)+,d1-d4/a0-a1
        move.l  name_step(pc),-(sp)
        rts

; mouse.s parameters: position, rectangle, RAWMOUSE slot, hide counter (A4),
; native sprite move (H0); then name entry: selected cell, columns (A4),
; native grid step (H0).
mouse_params_en:
        dc.w    2696,2728,162,-1160
        dc.l    $3171e
        dc.w    17716,17706
        dc.l    $16c66
mouse_params_de:
        dc.w    2740,2772,206,-1116
        dc.l    $318e0
        dc.w    17766,17756
        dc.l    $16d04
name_step:      dc.l 0
name_used:      dc.w 0,0,0
mouse_fields:   dc.w 0                  ; VBL pad reads

; Raw patch lists (no includes in this build): command, long offset, argument.
fix_patch_en:
        dc.w    3                ; PL_PS StoreNV's lowlevel call
        dc.l    $31498
        dc.w    bunk_store-fix_patch_en
        dc.w    2                ; PL_P GetNVList wrapper
        dc.l    $314b0
        dc.w    bunk_list_en-fix_patch_en
        dc.w    7                ; PL_W bne.s: save failure branch
        dc.l    $276b0
        dc.w    $6604
        dc.w    7                ; PL_W move.w (a2),-(sp): TrainSim choice
        dc.l    $1827e
        dc.w    $3f12
        dc.w    3                ; PL_PS room routine position stores
        dc.l    $273fc
        dc.w    mouse_room-fix_patch_en
        dc.w    3                ; PL_PS room exit sprite move
        dc.l    $27362
        dc.w    mouse_exit-fix_patch_en
        dc.w    3                ; PL_PS VBL port-1 pad read, after Psygore's
        dc.l    $33e78
        dc.w    mouse_pad-fix_patch_en
        dc.w    3                ; PL_PS pad record reset: click release guard
        dc.l    $33de6
        dc.w    mouse_guard-fix_patch_en
        dc.w    3                ; PL_PS name entry grid poll
        dc.l    $16ed0
        dc.w    mouse_name-fix_patch_en
        dc.w    0
fix_patch_de:
        dc.w    3
        dc.l    $3165a
        dc.w    bunk_store-fix_patch_de
        dc.w    2
        dc.l    $31672
        dc.w    bunk_list_de-fix_patch_de
        dc.w    7
        dc.l    $27872
        dc.w    $6604
        dc.w    7
        dc.l    $18338
        dc.w    $3f12
        dc.w    3
        dc.l    $275be
        dc.w    mouse_room-fix_patch_de
        dc.w    3
        dc.l    $27524
        dc.w    mouse_exit-fix_patch_de
        dc.w    3
        dc.l    $3403a
        dc.w    mouse_pad-fix_patch_de
        dc.w    3
        dc.l    $33fa8
        dc.w    mouse_guard-fix_patch_de
        dc.w    3
        dc.l    $16f6e
        dc.w    mouse_name-fix_patch_de
        dc.w    0

; StoreNV(a1 item name, a2 data, d0 size): as Psygore's S:16b6, but returns
; 0 (success). resload_SaveFile does not return on failure.
bunk_store:
        movea.l a1,a0
        movea.l a2,a1
        movea.l slave+$121e(pc),a2
        jsr     12(a2)           ; resload_SaveFile
        moveq   #0,d0
        addi.l  #$c,(sp)         ; continue at the wrapper's register restore
        rts

; GetNVList wrapper (array.l, count.w on the stack). Clears count flags and
; sets a flag for each Bed_N file that exists, named as the game names items
; (prefix, tens digit when nonzero, units digit). Preserves d2-d7/a2-a7.
bunk_list_en:
        movem.l d2/a2-a3,-(sp)
        movea.l -1328(a4),a3     ; item prefix "Bed_"
        bra.s   bunk_list
bunk_list_de:
        movem.l d2/a2-a3,-(sp)
        movea.l -1284(a4),a3
bunk_list:
        lea     -32(sp),sp       ; name buffer
        moveq   #0,d2
.next:
        cmp.w   32+12+8(sp),d2
        bhs.s   .done
        movea.l 32+12+4(sp),a0
        clr.b   (a0,d2.w)
        movea.l a3,a0
        movea.l sp,a1
        moveq   #32-4,d1         ; room for two digits and the terminator
.copy:
        move.b  (a0)+,(a1)+
        dbeq    d1,.copy
        bne.s   .done            ; overlong prefix: report nothing present
        subq.l  #1,a1
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #10,d0
        tst.b   d0
        beq.s   .units
        addi.b  #'0',d0
        move.b  d0,(a1)+
.units:
        swap    d0
        addi.b  #'0',d0
        move.b  d0,(a1)+
        clr.b   (a1)
        movea.l sp,a0
        movea.l slave+$121e(pc),a2
        jsr     36(a2)           ; resload_GetFileSize
        tst.l   d0
        beq.s   .absent
        movea.l 32+12+4(sp),a0
        st      (a0,d2.w)
.absent:
        addq.w  #1,d2
        bra.s   .next
.done:
        lea     32(sp),sp
        movem.l (sp)+,d2/a2-a3
        rts

release_name:
        dc.b 'Wing Commander CD32',0
release_info:
        dc.b '2.0b (13.11.2026)',10
        dc.b 'Original slave: Psygore',10
        dc.b 'Enhancements: Vesuri',0
release_version:
        dc.b '$VER: WingCommanderCD32 2.0b (13.11.2026)',0
release_config:
        dc.b 'C1:L:Language:English,German;'
        dc.b 'C2:L:Cheats:Off,Enabled,Invincible;'
        dc.b 'C3:L:System:Default,Enyo,McAuliffe,Gateway,Gimle,Brimstone,Chengdu,Dakota,Port Hedland,Kurasawa,Rostov,Hubble''s Star,Venice,Hell''s Kitchen;'
        dc.b 'C4:L:Mission:1,2,3;'
        dc.b 'C5:L:Mode:Enhanced,Psygore normal,Psygore unlimited,Psygore relaxed,Psygore slow;',0
        cnop 0,4
