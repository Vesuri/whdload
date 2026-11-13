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

; Psygore's NV storage is files: StoreNV returned 1 (failure) after a
; successful resload_SaveFile and GetNVList returned without filling its
; presence array, so the game cleared a saved bunk until the next reload.
; This second list, applied after his, returns success, lists the existing
; Bed_N files and restores the save-failure branch he NOPed. All modes.
release_patchseg:
        bsr.w   timing_patchseg
        movem.l d0-d1/a0-a1,-(sp)
        lea     bunk_patch_en(pc),a0
        move.l  slave+$1de4(pc),d0
        subq.l  #1,d0
        bne.s   .english
        lea     bunk_patch_de(pc),a0
.english:
        movea.l d7,a1
        jsr     116(a2)          ; resload_PatchSeg
        movem.l (sp)+,d0-d1/a0-a1
        rts

; Raw patch lists (no includes in this build): command, long offset, argument.
bunk_patch_en:
        dc.w    3                ; PL_PS StoreNV's lowlevel call
        dc.l    $31498
        dc.w    bunk_store-bunk_patch_en
        dc.w    2                ; PL_P GetNVList wrapper
        dc.l    $314b0
        dc.w    bunk_list_en-bunk_patch_en
        dc.w    7                ; PL_W bne.s: save failure branch
        dc.l    $276b0
        dc.w    $6604
        dc.w    0
bunk_patch_de:
        dc.w    3
        dc.l    $3165a
        dc.w    bunk_store-bunk_patch_de
        dc.w    2
        dc.l    $31672
        dc.w    bunk_list_de-bunk_patch_de
        dc.w    7
        dc.l    $27872
        dc.w    $6604
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
        dc.b 'CD32 improvements: Vesuri',0
release_version:
        dc.b '$VER: WingCommanderCD32 2.0b (19.10.2026)',0
release_config:
        dc.b 'C1:L:Language:English,German;'
        dc.b 'C2:L:Cheats:Off,Enabled,Invincible;'
        dc.b 'C3:L:System:Default,Enyo,McAuliffe,Gateway,Gimle,Brimstone,Chengdu,Dakota,Port Hedland,Kurasawa,Rostov,Hubble''s Star,Venice,Hell''s Kitchen;'
        dc.b 'C4:L:Mission:1,2,3;'
        dc.b 'C5:L:Mode:Enhanced,Psygore normal,Psygore unlimited,Psygore relaxed,Psygore slow;',0
        cnop 0,4
