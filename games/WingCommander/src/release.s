; Translate public language/pacing options once before language selection.
; Internal CUSTOM1=3 is reserved for enhanced English; 0/1 are Psygore.
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
        tst.l   d2
        beq.s   .enhanced
        subq.l  #1,(a1)          ; public 1..4 -> Psygore 0..3
        bra.s   .ready
.enhanced:
        tst.l   (a0)
        bne.s   .ready           ; German: normal until ported
        move.l  #3,(a0)
.ready:
        movem.l (sp)+,d0-d2/a0-a1
        bra.l   render_setcpu
.bad:
        movem.l (sp)+,d0-d2/a0-a1
        bra.w   timing_bad

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
release_patchseg:
        bsr.w   timing_patchseg
        movem.l d0-d1/a0-a1,-(sp)
        lea     fix_patch_en(pc),a0
        lea     mouse_params_en(pc),a1
        move.l  slave+$1de4(pc),d0
        subq.l  #1,d0
        bne.s   .english
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
        movem.l (sp)+,d0-d1/a0-a1
        rts

; Port-1 pad read in the VBL server (Psygore's S:1c2e); the left mouse button
; (CIA-A PRA bit 6) adds the red button, which the game decodes as fire.
mouse_pad:
        bsr.w   slave+$1c2e
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

; mouse.s parameters: position, rectangle, RAWMOUSE slot, hide counter (A4),
; native sprite move (H0).
mouse_params_en:
        dc.w    2696,2728,162,-1160
        dc.l    $3171e
mouse_params_de:
        dc.w    2740,2772,206,-1116
        dc.l    $318e0

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
        dc.b '2.0b (19.10.2026)',10
        dc.b 'Original slave: Psygore',10
        dc.b 'Enhancements: Vesuri',0
release_version:
        dc.b '$VER: WingCommanderCD32 2.0b (19.10.2026)',0
release_config:
        dc.b 'C1:L:Language:English,German;'
        dc.b 'C2:L:Cheats:Off,Enabled,Invincible;'
        dc.b 'C3:L:System:Default,Enyo,McAuliffe,Gateway,Gimle,Brimstone,Chengdu,Dakota,Port Hedland,Kurasawa,Rostov,Hubble''s Star,Venice,Hell''s Kitchen;'
        dc.b 'C4:L:Mission:1,2,3;'
        dc.b 'C5:L:Mode:Enhanced,Psygore normal,Psygore unlimited,Psygore relaxed,Psygore slow;',0
        cnop 0,4
