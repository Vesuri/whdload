; F1GP loader, reconstructed from the documented v1.0 behaviour.
; Original game and compressed names are local verified inputs, never vendored.
        INCLUDE whdload.i
        INCLUDE whdmacros.i

        IFND DEVELOPER
DEVELOPER = 0
        ENDC
        IFND VERIFY
VERIFY = 0
        ENDC
        IFNE DEVELOPER
slv_Version = 20             ; ws_MemConfig: E2-E4's fast areas; resload_Log (VERIFY)
        ELSE
slv_Version = 17
        ENDC
slv_Flags = WHDLF_NoError|WHDLF_EmulPriv|WHDLF_ClearMem|WHDLF_Examine
slv_keyexit = $59
CHIPMEMSIZE = $80000
FASTMEMSIZE = $80000
; Developer: MEMCONFIG=1 adds ExpMem for E2's copy, E3's picture, E4's shadows and E4's
; renderer data on machines with fast RAM. The default stays the release's, which a chip-only 2 MB A1200
; can still allocate (it cannot spare about 32 KB more).
E_AREAS = $29000
NUMDRIVES = 1
WPDRIVES = %1111
; Original KickEmu uses a 10,000-byte filesystem I/O cache.
IOCACHE = 10000
HDINIT
DOSASSIGN
BOOTDOS
        INCLUDE whdload/kick13.s

slv_CurrentDir dc.b 'data',0
slv_name dc.b 'Formula One Grand Prix',0
slv_copy dc.b '1991 Microprose',0
slv_info dc.b 'Reconstructed loader',10,'Original install by Codetapper/Action!',0
        IFNE DEVELOPER
        EVEN
slv_MemConfig dc.l CHIPMEMSIZE,$40000+FASTMEMSIZE+E_AREAS  ; kick13.s's KICKSIZE first
        dc.l 0
        ENDC
slv_config
        dc.b 'C1:B:Skip intro;'
        dc.b 'C2:X:Enable CPU caches:0;'
        IFNE DEVELOPER
        dc.b 'C2:X:Developer - VBL world clock:1;'
        dc.b 'C2:X:Developer - VBL world clock on a 68000 too:2;'
        dc.b 'C2:X:Developer - presentation snapshots and timing:3;'
        dc.b 'C2:X:Developer - hunk 2 code in fast RAM:4;'
        dc.b 'C2:X:Developer - draw in fast RAM:5;'
        dc.b 'C2:X:Developer - copy only changed blocks:6;'
        dc.b 'C2:X:Developer - renderer data in fast RAM:7;'
        dc.b 'C2:X:Developer - faster game routines:8;'
        dc.b 'C3:X:Ceiling - no pacer wait:0;'
        dc.b 'C3:X:Ceiling - no polygon fill:1;'
        dc.b 'C4:X:Ceiling - no preference notifications:0;'
        dc.b 'C4:X:C2 diagnostic - 20 field delay per batch:1;'
        dc.b 'C4:X:C2 diagnostic - retain native painting:2;'
        ENDC
        IFNE VERIFY
        dc.b 'C5:X:Verify pacer relay:0;'
        dc.b 'C5:X:Verify D3 - draw the previous tick:1;'
        dc.b 'C5:X:Verify E3 - blits twinned with the blitter:2;'
        dc.b 'C5:X:Verify E4 - changed-block copy compared:3;'
        ENDC
        dc.b 0
intro_name dc.b 'frontend',0
game_name dc.b 'f1gp',0
empty_args dc.b 0
intuition_name dc.b 'intuition.library',0
        CNOP 0,4
assign1 dc.b 12,'F1GP_Disk_#1',0
        CNOP 0,4
assign2 dc.b 12,'F1GP_Disk_#2',0
        CNOP 0,4
assign3 dc.b 12,'F1GP_Disk_#3',0
        CNOP 0,4
assign4 dc.b 12,'F1GP_Disk_#4',0
        EVEN
custom_tags dc.l WHDLTAG_CUSTOM1_GET
skip_intro dc.l 0
        dc.l WHDLTAG_CUSTOM2_GET
cache_options dc.l 0
        IFNE DEVELOPER
        dc.l WHDLTAG_CUSTOM4_GET
preference_options dc.l 0
        ENDC
        IFNE VERIFY
        dc.l WHDLTAG_CUSTOM5_GET
verify_options dc.l 0
        ENDC
        dc.l 0
game_size dc.l 0
        IFNE VERIFY
verify_pacer_target dc.l 0
        ENDC

RUN_SEGMENT MACRO
        move.l d7,a1
        adda.l a1,a1
        adda.l a1,a1
        moveq #0,d0
        lea (empty_args,pc),a0
        movem.l d0/d7/a2/a6,-(sp)
        jsr (4,a1)
        movem.l (sp)+,d1/d7/a2/a6
        move.l d7,d1
        jsr (_LVOUnLoadSeg,a6)
        ENDM

_bootdos
        move.l (_resload,pc),a2
        lea (_dosname,pc),a1
        move.l 4.w,a6
        jsr (_LVOOldOpenLibrary,a6)
        move.l d0,a6
        move.l a0,-(sp)       ; retain original DOS entry stack convention
        ; Original policy: BaseMem NC, ExpMem/Slave CB. Without an MMU
        ; this disables caches globally; with MMU, Fast regions remain cacheable.
        move.l #$3b3d,d0
        move.l #$7f3f,d1
        jsr (resload_SetCPU,a2)
        lea (assign1,pc),a0
        suba.l a1,a1
        bsr _dos_assign
        lea (assign2,pc),a0
        suba.l a1,a1
        bsr _dos_assign
        lea (assign3,pc),a0
        suba.l a1,a1
        bsr _dos_assign
        lea (assign4,pc),a0
        suba.l a1,a1
        bsr _dos_assign
        IFNE DEVELOPER
        ; Read the measurement gate before SetPrefs; retain its original inputs.
        movem.l d0-d1/a0-a2,-(sp)
        lea (custom_tags,pc),a0
        move.l (_resload,pc),a2
        jsr (resload_Control,a2)
        movem.l (sp)+,d0-d1/a0-a2
        ENDC
        bsr fast_pointer
        bset #1,$bfe001
        lea (custom_tags,pc),a0
        move.l (_resload,pc),a2
        jsr (resload_Control,a2)
        btst #0,(cache_options+3,pc)
        beq.s cache_ready
        ; Chip/IO data caching is inhibited by Amiga hardware. WT avoids
        ; copyback requests there; Fast/Slave RAM may use copyback with MMU.
        ; Keep 030 write allocation enabled (the game runs in user mode).
        move.l #WCPUF_Base_WT|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC|WCPUF_BC|WCPUF_SS|WCPUF_SB,d0
        move.l #WCPUF_All,d1
        jsr (resload_SetCPU,a2)
cache_ready
        IFNE VERIFY
        bsr verify_cache
        ENDC
        move.l (skip_intro,pc),d0
        bne.s load_game
        move.b $bfe001,d0
        and.b #$c0,d0
        cmp.b #$c0,d0
        bne.s load_game
        lea (intro_name,pc),a0
        bsr file_size
        tst.l d0
        beq.s load_game
        lea (intro_name,pc),a0
        move.l a0,d1
        jsr (_LVOLoadSeg,a6)
        move.l d0,d7
        beq load_failed
        RUN_SEGMENT
load_game
        lea (game_name,pc),a0
        move.l a0,d1
        jsr (_LVOLoadSeg,a6)
        move.l d0,d7
        beq load_failed
        lea (game_name,pc),a0
        bsr file_size
        lea (game_size,pc),a0
        move.l d0,(a0)
        lea (patch_582992,pc),a0
        cmp.l #582992,d0
        beq.s patch_game
        lea (patch_582988,pc),a0
        cmp.l #582988,d0
        beq.s patch_game
        lea (patch_582780,pc),a0
        cmp.l #582780,d0
        bne wrong_version
patch_game
        IFNE DEVELOPER
        bsr c2_init
        ENDC
        move.l d7,a1
        move.l (_resload,pc),a2
        jsr (resload_PatchSeg,a2)
        IFNE DEVELOPER
        move.l (game_size,pc),d0
        cmp.l #582992,d0
        bne.s .patched
        move.l (_attnflags,pc),d0
        btst #0,d0            ; AFF_68010: any CPU above the 68000
        bne.s .clock
        btst #2,(cache_options+3,pc)
        beq.s .patched
.clock
        lea (patch_582992_clock,pc),a0
        move.l d7,a1
        jsr (resload_PatchSeg,a2)
        bsr e2_reserve
        bsr e3_reserve
        bsr e4_reserve
.patched
        ENDC
        bsr restore_names
        IFNE VERIFY
        ; This relay is only installed for the supplied, verified layout.
        move.l d7,d0
        lsl.l #2,d0
        add.l #4+$1272,d0
        lea (verify_pacer_target,pc),a0
        move.l d0,(a0)
        ENDC
        RUN_SEGMENT
quit
        pea TDREASON_OK
        move.l (_resload,pc),a2
        jmp (resload_Abort,a2)
load_failed
        moveq #0,d0
        rts
wrong_version
        pea TDREASON_WRONGVER
        move.l (_resload,pc),a2
        jmp (resload_Abort,a2)

file_size
        movem.l d1/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_GetFileSize,a2)
        movem.l (sp)+,d1/a0-a2
        rts
fast_pointer
        movem.l d0-a6,-(sp)
        lea (intuition_name,pc),a1
        moveq #0,d0
        move.l 4.w,a6
        jsr (_LVOOpenLibrary,a6)
        move.l d0,a6
        lea (-110,sp),sp
        move.l sp,a0
        moveq #110,d0
        jsr (-132,a6)        ; GetPrefs
        move.l sp,a0
        move.w #1,(108,a0)   ; PointerTicks
        move.l sp,a0
        moveq #110,d0
        IFNE DEVELOPER
        ; SetPrefs Inform=FALSE suppresses startup preference notifications.
        ; With the gate off, preserve the original nonzero D1 and notification.
        btst #0,(preference_options+3,pc)
        beq.s .original_inform
        moveq #0,d1
.original_inform
        ENDC
        jsr (-324,a6)        ; SetPrefs
        lea (110,sp),sp
        movem.l (sp)+,d0-a6
        rts
keyboard
        ror.b #1,d0
        eor.b #$ff,d0
        cmp.b (_keyexit,pc),d0
        beq quit
        IFNE DEVELOPER
        bra c4_key
        ELSE
        rts
        ENDC
restore_names
        movem.l d0-a6,-(sp)
        move.l d7,a1
        adda.l a1,a1
        adda.l a1,a1
        addq.l #4,a1
        move.l (game_size,pc),d0
        cmp.l #582780,d0
        beq.s names_old
        move.l ($91a,a1),a1
        bra.s names_check
names_old
        move.l ($910,a1),a1
names_check
        lea ($900,a1),a1
        cmp.l #'Carl',(a1)
        bne.s names_done
        cmp.l #'os S',(4,a1)
        bne.s names_done
        lea (names_rnc,pc),a0
        move.l (_resload,pc),a2
        jsr (resload_Decrunch,a2)
names_done
        movem.l (sp)+,d0-a6
        rts

        IFNE VERIFY
verify_cache
        movem.l d0-a6,-(sp)
        moveq #0,d0
        move.l (_attnflags,pc),d1
        btst #1,d1            ; AFF_68020: never MOVEC on a 68000
        beq.s verify_cache_log
        lea (read_cacr,pc),a5
        move.l 4.w,a6
        jsr (_LVOSupervisor,a6)
verify_cache_log
        move.l d0,-(sp)
        lea (cache_log,pc),a0
        move.l (_resload,pc),a2
        jsr (resload_Log,a2)
        addq.l #4,sp
        movem.l (sp)+,d0-a6
        rts
read_cacr
        machine 68020
        movec cacr,d0
        rte
        machine 68000
cache_log dc.b 'F1GP VERIFY CACR=%08lx',10,0
        EVEN
verify_pacer
        ; Stack-only tail call: no game register or X change. The original
        ; pacer's first MOVE replaces NZVC before those flags are consumed.
        move.l (verify_pacer_target,pc),-(sp)
        rts
        ENDC

        IFNE DEVELOPER
; C1 integer VBL accounting. Caller supplies a stable serial in D0.
; No hardware access, no partial ticks. A0 points to this clock's state.
WC_LAST       = 0
WC_CREDIT     = 4
WC_RATE       = 6
WC_PHASE      = 8
WC_BATCH      = 10
WC_OBSERVED   = 12
WC_CONSUMED   = 16
WC_DROPPED    = 20
WC_TICKS      = 24
WC_SIZE       = 28

; D0=serial, D1=50/60. Start a new accounting epoch.
world_clock_rebase
        move.l d0,WC_LAST(a0)
        clr.w WC_CREDIT(a0)
        move.w d1,WC_RATE(a0)
        clr.w WC_PHASE(a0)
        clr.w WC_BATCH(a0)
        clr.l WC_OBSERVED(a0)
        clr.l WC_CONSUMED(a0)
        clr.l WC_DROPPED(a0)
        clr.l WC_TICKS(a0)
        rts

; D0=serial. Clobbers D0-D2. Saturate before addition, including partial credit.
world_clock_observe
        move.l d0,d1
        sub.l WC_LAST(a0),d0
        move.l d1,WC_LAST(a0)
        add.l d0,WC_OBSERVED(a0)
        moveq #0,d1
        move.w WC_RATE(a0),d1
        sub.w WC_CREDIT(a0),d1
        cmp.l d1,d0
        bls.s .accept
        move.l d0,d2
        sub.l d1,d2
        add.l d2,WC_DROPPED(a0)
        move.l d1,d0
.accept
        add.w d0,WC_CREDIT(a0)
        rts

; Return next whole interval in D0, without changing credit. Clobbers D1.
world_clock_interval
        moveq #7,d0
        cmpi.w #60,WC_RATE(a0)
        beq.s .ntsc
        tst.w WC_PHASE(a0)
        beq.s .done
        moveq #6,d0
.done
        rts
.ntsc
        tst.w WC_PHASE(a0)
        bne.s .done
        moveq #8,d0
        rts

; Reserve one tick, or D0=0 when not due / four-tick batch exhausted.
; The caller increments WC_TICKS only at actual tick completion.
world_clock_take
        cmpi.w #4,WC_BATCH(a0)
        bcc.s .none
        bsr.s world_clock_interval
        cmp.w WC_CREDIT(a0),d0
        bhi.s .none
        sub.w d0,WC_CREDIT(a0)
        add.l d0,WC_CONSUMED(a0)
        addq.w #1,WC_BATCH(a0)
        addq.w #1,WC_PHASE(a0)
        moveq #3,d1
        cmpi.w #60,WC_RATE(a0)
        bne.s .phase
        moveq #1,d1
.phase
        and.w d1,WC_PHASE(a0)
        rts
.none
        moveq #0,d0
        rts
; C2 hooks for the supplied game only. All state remains in the slave.
c2_init
        movem.l d0-d2/a0-a2,-(sp)
        lea (c2_h0,pc),a0
        move.l d7,d0
        lsl.l #2,d0
        addq.l #4,d0
        move.l d0,(a0)+
        move.l d0,a1
        move.l (-4,a1),d1
        lsl.l #2,d1
        addq.l #4,d1
        move.l d1,(a0)+
        move.l d1,a1
        move.l (-4,a1),d2
        lsl.l #2,d2
        addq.l #4,d2
        move.l d2,(a0)
        lea (c2_pacer_rest,pc),a0
        add.l #$127c,d0
        move.l d0,(a0)
        lea (c2_submit,pc),a0
        add.l #$1da62,d2
        move.l d2,(a0)
        move.l (c2_h0,pc),d0
        lea (c2_target_h0,pc),a0
        moveq #(c2_target_h2-c2_target_h0)/4-1,d2
.target0
        add.l d0,(a0)+
        dbf d2,.target0
        move.l (c2_h2,pc),d0
        moveq #(c2_target_end-c2_target_h2)/4-1,d2
.target2
        add.l d0,(a0)+
        dbf d2,.target2
        bsr c2_hud_init
        movem.l (sp)+,d0-d2/a0-a2
        rts

; E2: hunk 2's main code (E2_LOW-E2_HIGH, tools/e2_tables.py) runs from a fast-RAM copy.
; At load, a span at the top of ExpMem is reserved when ExpMem is real fast RAM with
; MEMCONFIG=1's spare (68020+, with the clock patches); at the
; first live epoch the code is copied, and every relocated JSR/JMP operand in e2_patches
; that still holds its original target in the span, and the slave's own hunk 2 code
; targets, move to the copy. Data stays in chip and only safe entries are redirected,
; so chip and copy run the same code against the same data. Enabling at a tick keeps the
; race identical to the option off (the menus run at the original speed).
        INCLUDE e2.i
e2_reserve
        movem.l d0-d1/a0-a1/a6,-(sp)
        btst #4,(cache_options+3,pc)
        beq.s .done
        move.l (_attnflags,pc),d0
        btst #1,d0              ; AFF_68020
        beq.s .done
        move.l 4.w,a6
        lea ($142,a6),a0        ; MemList
.header
        move.l (a0),a0
        tst.l (a0)
        beq.s .done
        btst #2,($f,a0)         ; MEMF_FAST
        beq.s .header
        bsr e_spare
        bcs.s .done
        move.l ($18,a0),d0      ; mh_Upper
        sub.l #E2_HIGH-E2_LOW,d0
        and.w #$fff0,d0
        movea.l d0,a1
        move.l #E2_HIGH-E2_LOW,d0
        jsr (_LVOAllocAbs,a6)
        lea (e2_copy,pc),a0
        move.l d0,(a0)
.done
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts

e2_enable
        movem.l d0-d4/a0-a2,-(sp)
        move.l (e2_copy,pc),d1
        beq .done
        lea (e2_on,pc),a0
        tst.w (a0)
        bne .done
        move.w #1,(a0)
        movea.l (c2_h2,pc),a0
        adda.l #E2_LOW,a0
        movea.l d1,a1
        move.w #(E2_HIGH-E2_LOW)/4-1,d0
.copy
        move.l (a0)+,(a1)+
        dbf d0,.copy
        bsr e2_flush            ; the copy reaches memory before any jump to it
        sub.l (c2_h2,pc),d1
        sub.l #E2_LOW,d1        ; D1 = copy - original
        moveq #0,d4             ; operands moved
        lea (e2_patches,pc),a2
        move.w #E2_PATCHES-1,d3
.patch
        move.l (a2)+,d0
        movea.l (c2_h0,pc),a1
        bclr #31,d0
        beq.s .hunk
        movea.l (c2_h2,pc),a1
.hunk
        adda.l d0,a1            ; the operand
        move.w (-2,a1),d0
        cmp.w #$4eb9,d0         ; JSR abs.l
        beq.s .jump
        cmp.w #$4ef9,d0         ; JMP abs.l
        bne.s .next             ; replaced by a slave patch
.jump
        move.l (a1),d0
        bsr.s e2_inside
        bcc.s .next             ; a slave patch's target
        add.l d1,(a1)
        addq.w #1,d4
        move.l a1,d0
        bsr.s e2_inside
        bcc.s .next
        add.l d1,(0,a1,d1.l)    ; the same operand in the copy
.next
        dbf d3,.patch
        lea (c2_target_h2,pc),a2
        moveq #(c2_target_end-c2_target_h2)/4-1,d3
.target
        bsr.s e2_target
        dbf d3,.target
        lea (c2_hud_targets,pc),a2
        moveq #11,d3
.hud
        bsr.s e2_target
        bsr.s e2_target
        bsr.s e2_target
        addq.l #4,a2
        dbf d3,.hud
        bsr.s e2_flush
        IFNE VERIFY
        move.l d4,-(sp)
        move.l (e2_copy,pc),-(sp)
        lea (e2_log,pc),a0
        move.l (_resload,pc),a2
        jsr (resload_Log,a2)
        addq.l #8,sp
        ENDC
.done
        movem.l (sp)+,d0-d4/a0-a2
        rts
e2_target                       ; (A2)+ moves to the copy if it lies in the span
        move.l (a2),d0
        bsr.s e2_inside
        bcc.s .kept
        add.l d1,(a2)
.kept
        addq.l #4,a2
        rts
e2_inside                       ; carry set if D0 lies in the span of the chip original
        move.l d0,-(sp)
        sub.l (c2_h2,pc),d0
        sub.l #E2_LOW,d0
        cmp.l #E2_HIGH-E2_LOW,d0
        movem.l (sp)+,d0        ; flags kept
        rts
e2_flush
        movem.l d0-d1/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
e2_copy dc.l 0
e2_on dc.w 0
        IFNE VERIFY
e2_log dc.b 'F1GP VERIFY E2 copy=%08lx operands=%ld',10,0
        EVEN
        ENDC

; E3: the picture is drawn in fast RAM. Between acquire and publication the renderer's
; destinations h0+$1252/$1256 point to a persistent fast buffer that holds the last
; published picture, so drawing starts without waiting for the display and without the
; front-to-back copy. Blits on it run on the CPU: the scene's sky and ground fills take
; the game's own CPU path (h2+$1E13C clear) and queued blits run through e3_blit.
; Publication waits until the chip back buffer is no longer displayed, copies the picture
; into it and restores the native chip addresses, so outside that window every pointer
; is what it would be with the option off. A VBL watch measures D2's lead, because the
; next picture has already started when the previous one is displayed.
E3_SIZE = 32000
e3_reserve                      ; below hunk 2's copy, or at the top of real fast RAM
        movem.l d0-d1/a0-a1/a6,-(sp)
        btst #5,(cache_options+3,pc)
        beq.s .done
        move.l (_attnflags,pc),d0
        btst #1,d0              ; AFF_68020
        beq.s .done
        move.l 4.w,a6
        lea ($142,a6),a0        ; MemList
.header
        move.l (a0),a0
        tst.l (a0)
        beq.s .done
        btst #2,($f,a0)         ; MEMF_FAST
        beq.s .header
        bsr e_spare
        bcs.s .done
        move.l ($18,a0),d0      ; mh_Upper
        move.l (e2_copy,pc),d1
        beq.s .top
        move.l d1,d0
.top
        move.l #E3_SIZE,d1
        btst #6,(cache_options+3,pc)
        beq.s .size
        move.l #E3_SIZE*3,d1    ; E4: the chip bitmaps' shadows follow the picture
.size
        sub.l d1,d0
        and.w #$fff0,d0
        movea.l d0,a1
        move.l d1,d0
        jsr (_LVOAllocAbs,a6)
        lea (e3_buffer,pc),a0
        move.l d0,(a0)
        beq.s .done
        btst #6,(cache_options+3,pc)
        beq.s .done
        add.l #E3_SIZE,d0
        lea (e4_last,pc),a0
        move.l d0,(a0)
.done
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts

; A0 = a MEMF_FAST header. Carry clear when it is real fast RAM (not ExpMem in chip) and
; MEMCONFIG=1's spare ExpMem is there, so the game keeps all of the default's.
e_spare
        cmpi.l #$200000,($14,a0)
        bcs.s .rts
        move.l ($18,a0),d0      ; mh_Upper
        sub.l ($14,a0),d0       ; mh_Lower
        cmp.l #FASTMEMSIZE,d0   ; carry set: the default ExpMem
.rts
        rts

; E4: the renderer's CPU-only chip data (tools/e4_tables.py: the edge pool, the span mask
; table, the fillers' jump-offset words and the scene's two variable blocks in hunk 2)
; moves to fast RAM at the first live epoch, below E3's picture (68020+, MEMCONFIG=1's
; spare). Each region is copied, then every listed long that holds an address inside it
; moves by the same distance. Pointers stored elsewhere keep the chip original, which
; still holds the same bytes. The slave reaches the moved variables through e4_map.
        INCLUDE e4.i
e4_reserve
        movem.l d0-d1/a0-a1/a6,-(sp)
        btst #7,(cache_options+3,pc)
        beq.s .done
        move.l (_attnflags,pc),d0
        btst #1,d0              ; AFF_68020
        beq.s .done
        move.l 4.w,a6
        lea ($142,a6),a0        ; MemList
.header
        move.l (a0),a0
        tst.l (a0)
        beq.s .done
        btst #2,($f,a0)         ; MEMF_FAST
        beq.s .header
        bsr e_spare
        bcs.s .done
        move.l ($18,a0),d0      ; mh_Upper
        move.l (e2_copy,pc),d1
        beq.s .e3
        move.l d1,d0
.e3
        move.l (e3_buffer,pc),d1
        beq.s .top
        move.l d1,d0
.top
        sub.l #E4_DATA_SIZE,d0
        and.w #$fff0,d0
        movea.l d0,a1
        move.l #E4_DATA_SIZE,d0
        jsr (_LVOAllocAbs,a6)
        lea (e4_data,pc),a0
        move.l d0,(a0)
.done
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts

e4_move
        movem.l d0-d4/a0-a4,-(sp)
        move.l (e4_data,pc),d0
        beq .done
        lea (e4_moved,pc),a0
        tst.w (a0)
        bne .done
        lea (e4_bases,pc),a2
        move.l (c2_h0,pc),(a2)+
        move.l (c2_h1,pc),(a2)+
        movea.l (c2_h2,pc),a0
        move.l a0,(a2)+
        move.l (-4,a0),d1       ; hunk 3 follows hunk 2 in the segment list
        lsl.l #2,d1
        addq.l #4,d1
        move.l d1,(a2)
        lea (e4_regions,pc),a2
        lea (e4_spans,pc),a3
        moveq #E4_REGIONS-1,d3
.region
        move.w (a2)+,d0         ; hunk.w, low, high, fast offset
        lsl.w #2,d0
        lea (e4_bases,pc),a0
        movea.l (a0,d0.w),a0
        move.l (a2)+,d0
        adda.l d0,a0            ; the chip original
        move.l (a2)+,d1
        sub.l d0,d1             ; its size
        movea.l (e4_data,pc),a1
        adda.l (a2)+,a1         ; its fast copy
        move.l a0,(a3)+
        move.l d1,(a3)+
        move.l a1,d0
        sub.l a0,d0
        move.l d0,(a3)+         ; fast - chip
        lsr.l #1,d1
        subq.w #1,d1
.copy
        move.w (a0)+,(a1)+
        dbf d1,.copy
        dbf d3,.region
        lea (e4_moved,pc),a0
        move.w #1,(a0)          ; e4_map follows the spans from here
        lea (e4_operands,pc),a3
        move.w #E4_OPERANDS-1,d4
.operand
        move.l (a3)+,d0
        move.l d0,d1
        rol.l #6,d1
        and.w #%111100,d1       ; the hunk * 4
        lea (e4_bases,pc),a0
        movea.l (a0,d1.w),a0
        and.l #$0fffffff,d0
        adda.l d0,a0
        bsr.s e4_map            ; the live long, in a copy if it lies in a region
        movea.l a0,a4
        movea.l (a4),a0
        bsr.s e4_map
        move.l a0,(a4)
        dbf d4,.operand
        bsr e2_flush
.done
        movem.l (sp)+,d0-d4/a0-a4
        rts
; A0 = an address; moved to the fast copy if it lies in a moved region.
e4_map
        movem.l d0-d1/a1,-(sp)
        move.w (e4_moved,pc),d0
        beq.s .done
        lea (e4_spans,pc),a1
        moveq #E4_REGIONS-1,d1
.span
        move.l a0,d0
        sub.l (a1)+,d0
        cmp.l (a1)+,d0
        bcc.s .next
        adda.l (a1),a0
        bra.s .done
.next
        addq.l #4,a1
        dbf d1,.span
.done
        movem.l (sp)+,d0-d1/a1
        rts
e4_data dc.l 0
e4_bases ds.l 4
e4_spans ds.l E4_REGIONS*3      ; chip original, size, fast - chip
e4_moved dc.w 0

; h0+$1EF74 and h0+$1EFDE (CUSTOM2 bit 8): the edge tracer's X-major steps. Natively a
; Bresenham loop runs once per pixel of X and stores X when Y steps; here one division
; gives each scanline's X step, with the same error term, so the same dy X values are
; stored. D1 = dx >= D2 = dy > 0, D4 the first X, A0 the edge's X list. D4 ends at the
; last X, as D6, so the native loop exits at once; D3.W ends as natively, ~(dx/2), and
; only D5-D7, which the native exit restores, are used besides.
e4_trace_right
        bsr.s e4_trace_steps
        add.w d7,d4
        move.w d4,(a0)+
        move.w d2,d7
        bra.s .next
.step
        add.w d5,d4             ; X += q, plus 1 when the error term passes 0
        add.w d6,d3
        ble.s .store
        sub.w d2,d3
        addq.w #1,d4
.store
        move.w d4,(a0)+
.next
        subq.w #1,d7
        bne.s .step
        bra.s e4_trace_end
e4_trace_left
        bsr.s e4_trace_steps
        sub.w d7,d4
        move.w d4,(a0)+
        move.w d2,d7
        bra.s .next
.step
        sub.w d5,d4
        add.w d6,d3
        ble.s .store
        sub.w d2,d3
        subq.w #1,d4
.store
        move.w d4,(a0)+
.next
        subq.w #1,d7
        bne.s .step
e4_trace_end
        move.w d4,d6            ; the native loop's end test
        move.w d1,d3
        lsr.w #1,d3
        not.w d3
        rts
e4_trace_steps                  ; -> D5.W q = dx/dy, D6.W m = dx mod dy, D3.W the error
        moveq #0,d5             ; term and D7.W the first step, q/2+1
        move.w d1,d5
        divu.w d2,d5
        move.l d5,d6
        swap d6
        moveq #0,d3
        btst #0,d5
        beq.s .even
        move.w d2,d3
.even
        add.w d6,d3
        lsr.w #1,d3
        addq.w #1,d3
        sub.w d2,d3             ; ((q odd ? dy : 0) + m)/2 + 1 - dy
        move.w d5,d7
        lsr.w #1,d7
        addq.w #1,d7
        rts

; h0+$20E and h2+$1F41E (CUSTOM2 bit 8): the sky band's scenery strip, h3+$704-$1704,
; which h2+$1F320 builds at a session's setup and only the band's blit reads (rows of
; 128 bytes, at most 8 rows and 106 bytes from each plane's start). Natively the blitter
; reads it from chip RAM; E3's CPU blits read a fast copy, taken after each build.
e4_strip_build
        move.l a0,-(sp)
        movea.l (c2_h2,pc),a0
        adda.l #$1f320,a0
        jsr (a0)
        movem.l d0/a0-a1,-(sp)
        bsr.s e4_strip_chip
        lea (e4_strip,pc),a1
        move.w #$1000/4-1,d0
.copy
        move.l (a0)+,(a1)+
        dbf d0,.copy
        lea (e4_strip_valid,pc),a0
        move.w #1,(a0)
        movem.l (sp)+,d0/a0-a1
        movea.l (sp)+,a0
        rts
e4_sky_source                   ; -> A0 the strip + 2, as lea h3+$706
        move.l d0,-(sp)
        move.w (e3_soft,pc),d0
        and.w (e4_strip_valid,pc),d0
        beq.s .chip
        lea (e4_strip+2,pc),a0
        bra.s .done
.chip
        bsr.s e4_strip_chip
        addq.l #2,a0
.done
        move.l (sp)+,d0
        rts
e4_strip_chip                   ; -> A0 h3+$704
        move.l d0,-(sp)
        movea.l (c2_h2,pc),a0
        move.l (-4,a0),d0       ; hunk 3 follows hunk 2 in the segment list
        lsl.l #2,d0
        addq.l #4,d0
        movea.l d0,a0
        lea ($704,a0),a0
        move.l (sp)+,d0
        rts
e4_strip_valid dc.w 0
        CNOP 0,4
e4_strip ds.b $1000

; From c2_acquire: the chip back buffer is the one not submitted last; draw in fast RAM.
e3_acquire
        bsr c2_drain            ; native blits queued before this picture finish first
        movea.l (c2_h0,pc),a2
        adda.l #$124a,a2
        movea.l 4(a2),a3        ; front: the last submitted bitmap
        move.l (a2),d0
        cmp.l a3,d0
        bne.s .back
        movea.l (c2_h2,pc),a4
        adda.l #$231da,a4
        exg a0,a4
        bsr e4_map
        exg a0,a4
        add.l (a4),d0
.back
        lea (e3_chip,pc),a4
        move.l d0,(a4)
        move.l (e3_buffer,pc),d0
        move.l d0,8(a2)
        move.l d0,12(a2)
        lea (e3_valid,pc),a4
        tst.w (a4)
        bne.s .valid
        move.w #1,(a4)          ; first picture, or after native code owned the bitmaps
        movea.l a3,a0
        movea.l d0,a1
        bsr e3_copy
        lea (e4_slots,pc),a4
        clr.l (a4)+             ; neither chip bitmap is known to E4
        clr.l (a4)
.valid
        IFNE VERIFY
        btst #2,(verify_options+3,pc)
        beq.s .unchecked
        movea.l a3,a0
        bsr e3_sum
        lea (e3_front_sum,pc),a4
        move.l d0,(a4)+
        movea.l (e3_chip,pc),a0
        bsr e3_sum
        move.l d0,(a4)+         ; e3_back_sum
        move.w #1,(a4)          ; e3_back_unchecked
.unchecked
        ENDC
        lea (e3_drawing,pc),a4
        move.w #1,(a4)
        lea (e3_soft,pc),a4
        move.w #1,(a4)
        rts

; Wait until the chip back buffer is no longer displayed: after an E3 submission the VBL
; watch has seen it taken; otherwise A5's rule, the pending clear and a following VBL.
e3_free
        move.l d0,-(sp)
        move.w (e3_timed,pc),d0
        beq.s .classic
.watch
        move.w (e3_watch,pc),d0
        bne.s .watch
        bra.s .done
.classic
        movem.l a2,-(sp)
        movea.l (c2_h2,pc),a2
        adda.l #$1dab0,a2
.pending
        tst.b (a2)
        bne.s .pending
        move.l (c2_serial,pc),d0
.field
        cmp.l (c2_serial,pc),d0
        beq.s .field
        movem.l (sp)+,a2
.done
        move.l (sp)+,d0
        rts

; From c2_publish, after the HUD, blits and replay paint: the picture into the chip back
; buffer, and the renderer's pointers back to it.
e3_present
        movem.l d0-d1/a0-a2,-(sp)
        bsr e3_free
        IFNE VERIFY
        bsr e3_check_back
        ENDC
        movea.l (e3_buffer,pc),a0
        movea.l (e3_chip,pc),a1
        move.l (e4_last,pc),d0
        bne.s .changed
        bsr e3_copy
        bra.s .copied
.changed
        bsr e4_copy
.copied
        IFNE VERIFY
        btst #2,(verify_options+3,pc)
        beq.s .unchecked
        movea.l (c2_h0,pc),a0
        movea.l ($124e,a0),a0   ; the front, displayed throughout the picture
        bsr e3_sum
        cmp.l (e3_front_sum,pc),d0
        beq.s .unchecked
        lea (e3_stray,pc),a0
        addq.l #1,(a0)
.unchecked
        ENDC
        bsr.s e3_restore
        lea (e3_pictures,pc),a0
        addq.l #1,(a0)
        movem.l (sp)+,d0-d1/a0-a2
        rts
e3_restore                      ; the chip back buffer replaces the fast one
        movea.l (c2_h0,pc),a2
        move.l (e3_chip,pc),d0
        move.l ($1252,a2),d1    ; the external views draw 640 bytes in
        sub.l (e3_buffer,pc),d1
        add.l d0,d1
        move.l d1,($1252,a2)
        move.l d0,($1256,a2)
        lea (e3_drawing,pc),a2
        clr.w (a2)
        lea (e3_soft,pc),a2
        clr.w (a2)
        rts

; From c2_publish, right after the submission (its pending byte is set): the picture's
; D2 start and kind, measured by e3_vbl once displayed.
e3_submitted
        movem.l d0/a0,-(sp)
        lea (d2_pending,pc),a0
        move.w (a0),d0
        clr.w (a0)
        lea (e3_d2_start,pc),a0
        move.l (d2_start,pc),(a0)+
        move.w (d2_kind,pc),(a0)+
        move.w d0,(a0)+         ; e3_d2_pending
        move.w #1,(a0)+         ; e3_timed
        move.w #1,(a0)          ; e3_watch, armed last
        movem.l (sp)+,d0/a0
        rts
; From c2_vbl, while armed: at the first VBL with the request taken, the submitted bitmap
; is displayed and the other one free. This is the field d2_shown records in c2_acquire.
e3_vbl
        movem.l d0/a0,-(sp)
        movea.l (c2_h2,pc),a0
        adda.l #$1dab0,a0
        tst.b (a0)
        bne.s .done
        lea (e3_watch,pc),a0
        clr.w (a0)
        lea (e3_d2_pending,pc),a0
        tst.w (a0)
        beq.s .done
        clr.w (a0)
        move.l (c2_serial,pc),d0
        sub.l (e3_d2_start,pc),d0
        cmpi.l #$7fff,d0
        bls.s .store
        move.w #$7fff,d0
.store
        lea (d2_leads,pc),a0
        adda.w (e3_d2_kind,pc),a0
        move.w d0,(a0)
.done
        movem.l (sp)+,d0/a0
        rts

; From c3_suspend and c3_leave, after c3_retire: native code takes over the bitmaps.
; A picture still being drawn goes into the owned chip bitmap (retired by the caller),
; and the fast buffer is refreshed from the front at the next acquire.
e3_leave
        movem.l d0-d1/a0-a2,-(sp)
        move.l (e3_buffer,pc),d0
        beq.s .done
        move.w (e3_drawing,pc),d0
        beq.s .chip
        movea.l (e3_buffer,pc),a0
        movea.l (e3_chip,pc),a1
        bsr.s e3_copy
        bsr e3_restore
.chip
        lea (e3_valid,pc),a0
        clr.w (a0)
        lea (e3_d2_pending,pc),a0
        clr.l (a0)              ; with e3_timed
        clr.w 4(a0)             ; e3_watch
.done
        movem.l (sp)+,d0-d1/a0-a2
        rts

e3_copy                         ; A0 -> A1, one picture
        movem.l d0-d7/a0-a4,-(sp)
        move.w #E3_SIZE/40-1,d0
.copy
        movem.l (a0)+,d1-d7/a2-a4
        movem.l d1-d7/a2-a4,(a1)
        lea 40(a1),a1
        dbf d0,.copy
        movem.l (sp)+,d0-d7/a0-a4
        rts

; E4: the picture copy writes only the longs that differ from what the chip bitmap holds.
; Each chip bitmap has a shadow in fast RAM with the picture last copied into it, so the
; comparison reads fast RAM only. When a chip bitmap's contents are unknown (the first
; copies, or after a handoff), the whole picture is copied into it and its shadow.
e4_copy                         ; A0 the fast picture -> A1 the chip back buffer
        movem.l d0-d1/d5/d7/a0-a3,-(sp)
        lea (e4_slots,pc),a3
        movea.l (e4_last,pc),a2         ; the first chip bitmap's shadow
        cmpa.l (a3),a1
        beq.s .compare_from
        lea (E3_SIZE,a2),a2
        cmpa.l 4(a3),a1
        beq.s .compare_from
        tst.l 4(a3)
        beq.s .second
        lea (-E3_SIZE,a2),a2            ; a new bitmap takes the first shadow
        move.l a1,(a3)
        bra.s .whole
.second
        move.l a1,4(a3)
.whole
        bsr e3_copy
        movea.l a2,a1
        bsr e3_copy
        lea (e4_full,pc),a3
        addq.l #1,(a3)
        bra.s .done
.compare_from
        move.l a1,d5
        sub.l a2,d5                     ; chip bitmap - shadow
        moveq #0,d1
        move.w #E3_SIZE/4-1,d7
.compare
        cmpm.l (a0)+,(a2)+
        dbne d7,.compare
        beq.s .end
        move.l -4(a0),d0                ; a long that differs from the chip bitmap
        move.l d0,-4(a2)
        move.l d0,-4(a2,d5.l)
        addq.l #1,d1
        dbf d7,.compare
.end
        lea (e4_written,pc),a3
        add.l d1,(a3)
.done
        lea (e4_copies,pc),a3
        addq.l #1,(a3)
        movem.l (sp)+,d0-d1/d5/d7/a0-a3
        IFNE VERIFY
        btst #3,(verify_options+3,pc)
        beq.s .unchecked
        bsr e4_check
.unchecked
        ENDC
        rts

; The queued blits of one c2_blit_queue call (A0: word count - 1, then the commands the
; level-3 interrupt h2+$35E would write) on the CPU. Registers persist between blits
; as in the blitter. As natively, A0 ends after the block and D0.W is $FFFF.
e3_queue
        IFNE VERIFY
        btst #2,(verify_options+3,pc)
        beq.s .untwinned
        bsr e3_twin_queue
.untwinned
        ENDC
        movem.l d1-d2/a5-a6,-(sp)
        lea (e3_regs,pc),a6
        suba.w #$40,a6          ; indexed by custom register offset
        move.w (a0)+,d0
        addq.w #1,d0
        add.w d0,d0
        lea (a0,d0.w),a5        ; block end
.command
        cmpa.l a5,a0
        bcc.s .done
        move.w (a0)+,d1         ; long writes - 1
.long
        move.w (a0)+,d2
        bsr.s .register
        move.l (a0)+,(a6,d2.w)
        dbf d1,.long
.word
        move.w (a0)+,d2
        beq.s .size
        bsr.s .register
        move.w (a0)+,(a6,d2.w)
        bra.s .word
.size
        move.w (a0)+,d2         ; BLTSIZE
        bsr e3_blit
        bra.s .command
.register                       ; only $40-$77 lie in e3_regs; others are not supported
        cmpi.w #$40,d2
        bcs.s .other
        cmpi.w #$76,d2
        bls.s .known
.other
        move.l a0,-(sp)
        lea (e3_unsupported,pc),a0
        addq.l #1,(a0)
        movea.l (sp)+,a0
        moveq #$76,d2           ; the BLTADAT slot's spare
.known
        rts
.done
        IFNE VERIFY
        lea (e3_twin_pending,pc),a5
        tst.w (a5)
        beq.s .compared
        clr.w (a5)
        bsr e3_compare
.compared
        ENDC
        moveq #-1,d0
        movem.l (sp)+,d1-d2/a5-a6
        rts

; One blit on the CPU from the shadow registers (A6 = e3_regs-$40, D2 = BLTSIZE):
; channels A-D with shifts, first and last word masks, modulos and any minterm,
; ascending only. Line, descending and fill modes are counted and skipped.
E3_ROWS = $78
E3_COLUMN = $7a
E3_WIDTH = $7c
E3_BSHIFT = $7e
E3_ASHIFTED = $80
e3_blit
        movem.l d0-d7/a0-a3,-(sp)
        lea (e3_blits,pc),a0
        addq.l #1,(a0)
        move.w ($42,a6),d0      ; BLTCON1
        andi.w #$1b,d0          ; line, descending, inclusive or exclusive fill
        beq.s .supported
        lea (e3_unsupported,pc),a0
        addq.l #1,(a0)
        bra .done
.supported
        move.w d2,d0
        lsr.w #6,d0
        bne.s .rows
        move.w #1024,d0
.rows
        move.w d0,(E3_ROWS,a6)
        andi.w #$3f,d2
        bne.s .width
        moveq #64,d2
.width
        subq.w #1,d2
        move.w d2,(E3_WIDTH,a6)
        movea.l ($50,a6),a0     ; A
        movea.l ($4c,a6),a1     ; B
        movea.l ($48,a6),a2     ; C
        movea.l ($54,a6),a3     ; D
        move.w ($40,a6),d3      ; BLTCON0: shift, channels, minterm
        move.w d3,d7
        rol.w #4,d7
        andi.w #15,d7           ; A shift
        move.w ($42,a6),d0
        rol.w #4,d0
        andi.w #15,d0
        move.w d0,(E3_BSHIFT,a6)
        moveq #0,d4             ; previous B word
        moveq #0,d5             ; previous A word, masked
        move.w d3,d0
        andi.w #$0fff,d0
        cmpi.w #$07ca,d0        ; B, C and D, A constant: A ? B : C (the sky band)
        bne.s .row
        tst.w d7
        beq .band
.row
        move.w (E3_WIDTH,a6),(E3_COLUMN,a6)
.word
        move.w ($74,a6),d0      ; BLTADAT
        btst #11,d3
        beq.s .a
        move.w (a0)+,d0
.a
        move.w (E3_COLUMN,a6),d1
        bne.s .not_last
        and.w ($46,a6),d0       ; BLTALWM
.not_last
        cmp.w (E3_WIDTH,a6),d1
        bne.s .not_first
        and.w ($44,a6),d0       ; BLTAFWM
.not_first
        move.w d5,d1
        swap d1
        move.w d0,d1
        move.w d0,d5
        lsr.l d7,d1
        move.w d1,(E3_ASHIFTED,a6)
        move.w ($72,a6),d0      ; BLTBDAT
        btst #10,d3
        beq.s .b
        move.w (a1)+,d0
.b
        move.w d4,d1
        swap d1
        move.w d0,d1
        move.w d0,d4
        move.w (E3_BSHIFT,a6),d0
        lsr.l d0,d1             ; B
        move.w ($70,a6),d2      ; BLTCDAT
        btst #9,d3
        beq.s .c
        move.w (a2)+,d2         ; C
.c
        move.w (E3_ASHIFTED,a6),d0      ; A
        cmpi.b #$ca,d3          ; A ? B : C
        bne.s .copy
        and.w d0,d1
        not.w d0
        and.w d0,d2
        or.w d2,d1
        move.w d1,d6
        bra.s .d
.copy
        cmpi.b #$f0,d3          ; A
        bne.s .general
        move.w d0,d6
        bra.s .d
.general
        bsr e3_minterm
.d
        btst #8,d3
        beq.s .no_d
        move.w d6,(a3)+
.no_d
        subq.w #1,(E3_COLUMN,a6)
        bcc .word
        btst #11,d3
        beq.s .a_row
        adda.w ($64,a6),a0      ; BLTAMOD
.a_row
        btst #10,d3
        beq.s .b_row
        adda.w ($62,a6),a1      ; BLTBMOD
.b_row
        btst #9,d3
        beq.s .c_row
        adda.w ($60,a6),a2      ; BLTCMOD
.c_row
        btst #8,d3
        beq.s .d_row
        adda.w ($66,a6),a3      ; BLTDMOD
.d_row
        subq.w #1,(E3_ROWS,a6)
        bne .row
        move.l a0,($50,a6)      ; the pointers end where the blitter leaves them
        move.l a1,($4c,a6)
        move.l a2,($48,a6)
        move.l a3,($54,a6)
.done
        movem.l (sp)+,d0-d7/a0-a3
        rts
.band                           ; the same for that case, A unshifted
        move.w (E3_BSHIFT,a6),d5
        move.w (E3_ROWS,a6),d7
        subq.w #1,d7
.band_row
        move.w (E3_WIDTH,a6),d6
        move.w ($74,a6),d3
        and.w ($44,a6),d3
        tst.w d6
        bne.s .band_word
        and.w ($46,a6),d3
.band_word                      ; D3 = A
        move.w (a1)+,d0
        swap d4
        move.w d0,d4
        move.l d4,d1
        lsr.l d5,d1             ; B
        and.w d3,d1
        not.w d3
        and.w (a2)+,d3
        or.w d3,d1
        move.w d1,(a3)+
        subq.w #1,d6
        bcs.s .band_end
        beq.s .band_last
        move.w ($74,a6),d3
        bra.s .band_word
.band_last
        move.w ($74,a6),d3
        and.w ($46,a6),d3
        bra.s .band_word
.band_end
        adda.w ($62,a6),a1
        adda.w ($60,a6),a2
        adda.w ($66,a6),a3
        dbf d7,.band_row
        move.l a1,($4c,a6)
        move.l a2,($48,a6)
        move.l a3,($54,a6)
        bra.s .done
e3_minterm                      ; D0 A, D1 B, D2 C, D3 low byte the minterm -> D6
        movem.l d4-d5/d7,-(sp)
        moveq #0,d6
        moveq #7,d7
.term
        btst d7,d3
        beq.s .next
        move.w d0,d4
        btst #2,d7
        bne.s .a
        not.w d4
.a
        move.w d1,d5
        btst #1,d7
        bne.s .b
        not.w d5
.b
        and.w d5,d4
        move.w d2,d5
        btst #0,d7
        bne.s .c
        not.w d5
.c
        and.w d5,d4
        or.w d4,d6
.next
        dbf d7,.term
        movem.l (sp)+,d4-d5/d7
        rts

; h2+$27D62: the scene waits for the pending exchange, then selects queued blitter fills
; (h2+$1E13C bit 7). Drawing in fast RAM needs neither: the fills run on the CPU. Both
; paths continue at h2+$27D78.
e3_scene_wait
        move.l a0,-(sp)
        move.w (e3_soft,pc),-(sp)
        movea.l (c2_h2,pc),a0
        tst.w (sp)+
        bne.s .fast
        adda.l #$1dab0,a0
.pending
        tst.b (a0)
        bmi.s .pending
        movea.l (c2_h2,pc),a0
        adda.l #$1e13c,a0
        move.b #$80,(a0)
        bra.s .done
.fast
        adda.l #$1e13c,a0
        clr.b (a0)
.done
        movea.l (sp)+,a0
        addi.l #16,(sp)
        rts

        IFNE VERIFY
; CUSTOM5 bit 2: every operation E3 moves from the blitter to the CPU is twinned. The
; chip back buffer gets the fast picture, the blitter does the operation there, the CPU
; does it in fast RAM, and the two pictures are compared. Neither chip bitmap may change
; otherwise between acquire and publication (e3_stray).
e3_twin_begin                   ; the fast picture into the free chip back buffer
        movem.l a0-a1,-(sp)
        bsr e3_free
        bsr e3_check_back
        movea.l (e3_buffer,pc),a0
        movea.l (e3_chip,pc),a1
        bsr e3_copy
        movem.l (sp)+,a0-a1
        rts
e3_twin_chip                    ; h0+$1252 into the chip back buffer, blits on the blitter
        movem.l d1/a2,-(sp)
        movea.l (c2_h0,pc),a2
        move.l ($1252,a2),d1
        sub.l (e3_buffer,pc),d1
        add.l (e3_chip,pc),d1
        move.l d1,($1252,a2)
        lea (e3_soft,pc),a2
        clr.w (a2)
        movem.l (sp)+,d1/a2
        rts
e3_twin_fast                    ; and back
        movem.l d1/a2,-(sp)
        movea.l (c2_h0,pc),a2
        move.l ($1252,a2),d1
        sub.l (e3_chip,pc),d1
        add.l (e3_buffer,pc),d1
        move.l d1,($1252,a2)
        lea (e3_soft,pc),a2
        move.w #1,(a2)
        movem.l (sp)+,d1/a2
        rts

; From c2_clear, with the registers h2+$1E158 receives: the row fill by the blitter
; (h2+$1E13C bit 7) into chip, then by the game's CPU path, E3's, into fast RAM.
e3_twin_fill
        movem.l d0-a6,-(sp)
        bsr e3_twin_begin
        bsr e3_twin_chip
        movea.l (c2_h2,pc),a0
        adda.l #$1e13c,a0
        move.b #$80,(a0)
        movem.l (sp),d0-a6
        bsr.s .fill
        bsr c2_drain
        bsr e3_twin_fast
        movea.l (c2_h2,pc),a0
        adda.l #$1e13c,a0
        clr.b (a0)
        movem.l (sp),d0-a6
        bsr.s .fill
        bsr e3_compare
        movem.l (sp)+,d0-a6
        rts
.fill                           ; the rest of h2+$1E13E, back here
        movem.l d0-a6,-(sp)     ; popped by its own epilogue
        move.l (c2_clear_rest,pc),-(sp)
        rts

; From e3_queue (A0: the block): the blitter runs a copy of the block whose pointers
; into the fast picture (and up to 64 bytes around it) are moved to the chip one.
E3_BLOCK = 512
e3_twin_queue
        movem.l d0-d3/a0-a2,-(sp)
        bsr e3_twin_begin
        lea (e3_twin_block,pc),a1
        move.w (a0)+,d0         ; words - 1
        cmpi.w #E3_BLOCK/2-2,d0
        bls.s .fits
        lea (e3_unsupported,pc),a2
        addq.l #1,(a2)
        lea (e3_twin_pending,pc),a2
        clr.w (a2)
        bra.s .done
.fits
        move.w d0,(a1)+
        movea.l a0,a2
        addq.w #1,d0
        add.w d0,d0
        adda.w d0,a0            ; the block's end
.command
        cmpa.l a0,a2
        bcc.s .copied
        move.w (a2)+,d1         ; long writes - 1
        move.w d1,(a1)+
.long
        move.w (a2)+,d2
        move.w d2,(a1)+
        move.l (a2)+,d3
        cmpi.w #$48,d2          ; BLTCPT, BLTBPT, BLTAPT, BLTDPT
        bcs.s .store
        cmpi.w #$54,d2
        bhi.s .store
        move.l d3,d0
        sub.l (e3_buffer,pc),d0
        addi.l #64,d0
        cmpi.l #E3_SIZE+128,d0
        bcc.s .store
        sub.l (e3_buffer,pc),d3
        add.l (e3_chip,pc),d3
.store
        move.l d3,(a1)+
        dbf d1,.long
.word
        move.w (a2)+,d2
        move.w d2,(a1)+
        beq.s .size
        move.w (a2)+,(a1)+
        bra.s .word
.size
        move.w (a2)+,(a1)+      ; BLTSIZE
        bra.s .command
.copied
        bsr e3_twin_chip
        lea (e3_twin_block,pc),a0
        bsr.s .queue
        bsr c2_drain
        bsr e3_twin_fast
        lea (e3_twin_pending,pc),a2
        move.w #1,(a2)
.done
        movem.l (sp)+,d0-d3/a0-a2
        rts
.queue                          ; h2+$1E6CC's own body, A0 the block
        move.l a1,-(sp)
        movea.l (c2_h2,pc),a1
        adda.l #$1e2e4,a1
        move.l (c2_queue_rest,pc),-(sp)
        rts

e3_compare                      ; the fast and the chip picture
        movem.l d0/a0-a2,-(sp)
        lea (e3_twins,pc),a2
        addq.l #1,(a2)
        movea.l (e3_buffer,pc),a0
        movea.l (e3_chip,pc),a1
        move.w #E3_SIZE/4-1,d0
.compare
        cmpm.l (a0)+,(a1)+
        dbne d0,.compare
        tst.w d0
        bmi.s e3_compare_same
e3_fault                        ; c5_capture --twin saves both pictures here
        lea (e3_faults,pc),a2
        addq.l #1,(a2)+
        tst.l (a2)
        bne.s e3_compare_same
        subq.l #4,a0
        suba.l (e3_buffer,pc),a0
        addq.l #1,a0
        move.l a0,(a2)+         ; e3_first: byte offset + 1
        move.l (c2_clock+WC_TICKS,pc),(a2)      ; e3_first_tick
e3_compare_same
        movem.l (sp)+,d0/a0-a2
        rts
; E4: after the changed-block copy the chip back buffer holds the whole fast picture.
e4_check
        movem.l d0/a0-a2,-(sp)
        lea (e4_checks,pc),a2
        addq.l #1,(a2)
        movea.l (e3_buffer,pc),a0
        movea.l (e3_chip,pc),a1
        move.w #E3_SIZE/4-1,d0
.compare
        cmpm.l (a0)+,(a1)+
        dbne d0,.compare
        tst.w d0
        bmi.s .same
        lea (e4_faults,pc),a2
        addq.l #1,(a2)+
        tst.l (a2)
        bne.s .same
        subq.l #4,a0
        suba.l (e3_buffer,pc),a0
        addq.l #1,a0
        move.l a0,(a2)+         ; e4_first: byte offset + 1
        move.l (c2_clock+WC_TICKS,pc),(a2)      ; e4_first_tick
.same
        movem.l (sp)+,d0/a0-a2
        rts
; The chip back buffer, untouched since acquire, before its first overwrite.
e3_check_back
        movem.l d0/a0,-(sp)
        btst #2,(verify_options+3,pc)
        beq.s .done
        lea (e3_back_unchecked,pc),a0
        tst.w (a0)
        beq.s .done
        clr.w (a0)
        movea.l (e3_chip,pc),a0
        bsr.s e3_sum
        cmp.l (e3_back_sum,pc),d0
        beq.s .done
        lea (e3_stray,pc),a0
        addq.l #1,(a0)
.done
        movem.l (sp)+,d0/a0
        rts
e3_sum                          ; A0 -> D0, the sum of a picture's longs
        movem.l d1/a0,-(sp)
        moveq #0,d0
        move.w #E3_SIZE/4-1,d1
.sum
        add.l (a0)+,d0
        dbf d1,.sum
        movem.l (sp)+,d1/a0
        rts
e3_log_counts
        movem.l d0-d1/a0-a2,-(sp)
        move.l (e3_buffer,pc),d0
        beq.s .done
        move.l (e3_unsupported,pc),-(sp)
        move.l (e3_blits,pc),-(sp)
        move.l (e3_stray,pc),-(sp)
        move.l (e3_first_tick,pc),-(sp)
        move.l (e3_first,pc),-(sp)
        move.l (e3_faults,pc),-(sp)
        move.l (e3_twins,pc),-(sp)
        move.l (e3_pictures,pc),-(sp)
        move.l d0,-(sp)
        lea (e3_log,pc),a0
        move.l (_resload,pc),a2
        jsr (resload_Log,a2)
        lea 36(sp),sp
        move.l (e4_last,pc),d0
        beq.s .done
        move.l (e4_first_tick,pc),-(sp)
        move.l (e4_first,pc),-(sp)
        move.l (e4_faults,pc),-(sp)
        move.l (e4_checks,pc),-(sp)
        move.l (e4_written,pc),-(sp)
        move.l (e4_full,pc),-(sp)
        move.l (e4_copies,pc),-(sp)
        lea (e4_log,pc),a0
        jsr (resload_Log,a2)
        lea 28(sp),sp
.done
        movem.l (sp)+,d0-d1/a0-a2
        rts
e4_log dc.b 'F1GP VERIFY E4 copies=%ld full=%ld longs=%ld checks=%ld faults=%ld'
        dc.b ' first=%ld tick=%ld',10,0
e3_log dc.b 'F1GP VERIFY E3 buffer=%08lx pictures=%ld twins=%ld faults=%ld'
        dc.b ' first=%ld tick=%ld stray=%ld blits=%ld unsupported=%ld',10,0
        EVEN
        ENDC

        CNOP 0,4
e3_buffer dc.l 0                ; the fast picture; 0: E3 unavailable
e3_chip dc.l 0                  ; the chip back buffer of the picture being drawn
e3_pictures dc.l 0              ; pictures published from fast RAM
e3_blits dc.l 0                 ; blits run on the CPU
e3_unsupported dc.l 0           ; blit modes or registers e3_blit does not run
e3_d2_start dc.l 0              ; D2: the submitted picture's start field
e3_d2_kind dc.w 0
e3_d2_pending dc.w 0            ; its displayed field not yet seen
e3_timed dc.w 0                 ; the last submission was watched
e3_watch dc.w 0                 ; e3_vbl waits for it to be taken
e3_drawing dc.w 0               ; h0+$1252/$1256 point to the fast picture
e3_soft dc.w 0                  ; blits run on the CPU
e3_valid dc.w 0                 ; the fast picture holds the last published one
e4_last dc.l 0                  ; E4: the chip bitmaps' shadows; 0: off
e4_slots dc.l 0,0               ; the chip bitmap of each shadow; 0: unknown
e4_copies dc.l 0                ; pictures copied by E4
e4_full dc.l 0                  ; of them copied whole
e4_written dc.l 0               ; longs written by the others
e3_regs ds.b $48                ; blitter registers $40-$77, then e3_blit's scratch
        IFNE VERIFY
        CNOP 0,4
e3_front_sum dc.l 0
e3_back_sum dc.l 0
e3_back_unchecked dc.w 0
e3_twin_pending dc.w 0          ; e3_queue compares after its blits
        CNOP 0,4
e3_twins dc.l 0                 ; operations twinned
e3_faults dc.l 0                ; twins that differ
e3_first dc.l 0                 ; the first difference's byte offset + 1
e3_first_tick dc.l 0
e3_stray dc.l 0                 ; chip bitmaps changed between acquire and publication
e4_checks dc.l 0                ; E4 copies compared with the fast picture
e4_faults dc.l 0                ; that differ
e4_first dc.l 0                 ; the first difference's byte offset + 1
e4_first_tick dc.l 0
e3_twin_block ds.b E3_BLOCK
        ENDC

c2_live_entry
        bsr c3_leave_restart
        move.l a0,-(sp)
        lea (c2_mode,pc),a0
        clr.w (a0)
        lea (c2_in_tick,pc),a0
        clr.w (a0)
        movea.l (sp)+,a0
        move.l (c2_native_entry,pc),-(sp)
        rts

c2_vbl
        move.l a0,-(sp)
        lea (c2_serial,pc),a0
        addq.l #1,(a0)
        lea (e3_watch,pc),a0
        tst.w (a0)
        beq.s .unwatched
        bsr e3_vbl
.unwatched
        move.l (c2_h0,pc),a0
        ; Reproduce the stolen instruction last, including its X/N/Z/V/C.
        adda.l #$125e,a0
        addq.w #1,(a0)
        movea.l (sp)+,a0
        rts

c2_live_head
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        moveq #1,d7
        bra.s c2_head
c2_replay_head
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        moveq #2,d7
c2_head
        lea (c2_clock,pc),a0
        lea (c2_mode,pc),a1
        cmp.w (a1),d7
        beq.s .same_epoch
        lea (c2_scene_ready,pc),a1
        clr.w (a1)
        move.l (c2_h2,pc),a2
        adda.l #$2a650,a2
        lea (c2_native_rate,pc),a1
        move.w (a2),(a1)
        bsr c2_field_rate
        move.l (c2_serial,pc),d0
        lea (c3_inactive,pc),a1
        tst.w (a1)
        beq.s .initial
        clr.w (a1)
        move.l d0,d2
        sub.l (c3_idle_start,pc),d2
        lea (c3_excluded,pc),a1
        add.l d2,(a1)
.initial
        bsr e4_move             ; before E2's copy, which then holds the moved operands
        bsr e2_enable
        bsr world_clock_rebase
        lea (c2_mode,pc),a1
        move.w d7,(a1)
        lea (c3_rebased,pc),a1
        clr.l (a1)
        lea (c3_epochs,pc),a1
        addq.l #1,(a1)
        lea (c2_sound_serial,pc),a1
        move.l d0,(a1)
.same_epoch
        tst.w WC_BATCH(a0)
        bne.s .observe
        bsr c2_acquire
.observe
        lea (c2_clock,pc),a0
        move.l (c2_serial,pc),d0
        bsr world_clock_observe
        bsr world_clock_take
        tst.w d0
        bne.s .tick_due
        move.w (c2_scene_ready,pc),d0
        beq.s .observe
        movea.l (c2_h0,pc),a2
        adda.l #$3a6e2,a2
        tst.b (a2)
        bne.s .observe
        bsr c2_repeat_picture
        bsr c2_acquire
        bra.s .observe
.tick_due
        move.l (c2_h0,pc),a2
        ; Native external-view selection adds 640 to the draw destination.
        ; Restart from the owned bitmap on every tick, including catch-up.
        move.l ($1256,a2),($1252,a2)
        adda.l #$125a,a2
        move.w d0,(a2)
        lea (c2_sound_serial,pc),a1
        move.l (c2_serial,pc),d0
        move.l d0,d1
        sub.l (a1),d1
        move.l d0,(a1)
        cmpi.l #32767,d1
        bls.s .sound
        move.l #32767,d1
.sound
        move.w d1,2(a2)
        clr.w 4(a2)            ; native renderer work counter, not world time
        lea (c2_draw_mode,pc),a1
        move.w #1,(a1)
        cmpi.w #4,WC_BATCH(a0)
        bcc.s .selected
        bsr world_clock_interval
        cmp.w WC_CREDIT(a0),d0
        bhi.s .selected
        move.w #2,(a1)         ; tick-only pass: another whole tick is already due
.selected
        lea (c2_in_tick,pc),a1
        move.w #1,(a1)
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        move.l a0,-(sp)
        movea.l (c2_h0,pc),a0
        adda.l #$2cc32,a0
        tst.l (a0)            ; native header instruction, supplies branch flags
        movea.l (sp)+,a0
        rts

; C3 modal handoffs. A suspended native tick remains reserved and completes
; once after resume. Its accumulated credit is explicitly rebased, never dropped.
; Outside a live/replay epoch the native pacer and modal painters retain ownership.
c3_live_pause
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        move.w (c2_mode,pc),d0
        cmpi.w #2,d0
        bne.s .live
        bsr c3_leave_replay_end  ; replay ends before returning to live pause
.live
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        bsr .native
        bsr c3_resume
        ; Menu return and replay completion bypass the ordinary live header.
        ; Reserve a tick here only if native control actually continues live.
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        move.w (c2_in_tick,pc),d0
        bne.s .done
        movea.l (c2_h2,pc),a0
        adda.l #$2a75e,a0
        btst #4,(a0)
        bne.s .done
        movea.l (c2_h0,pc),a0
        adda.l #$3a70c,a0
        tst.b (a0)
        beq.s .schedule
        tst.b ($c0,a0)
        bpl.s .done
.schedule
        bsr c2_live_head
.done
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        rts
.native
        move.l (c3_native_live_pause,pc),-(sp)
        rts

c3_replay_pause
        bsr .native
        bra c3_resume
.native
        move.l (c3_native_replay_pause,pc),-(sp)
        rts

; Both wait entries replace the native audio-off JSR. Queued UI is made visible
; before native modal code may touch both bitmaps. No enhanced painting while idle.
c3_pause_begin
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        move.w (c2_in_tick,pc),d0
        beq.s .done
        bsr c3_suspend
        lea (c3_pauses,pc),a0
        addq.l #1,(a0)
.done
        bsr c4_flush            ; the native wait polls keys without tick scans
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        bra c3_audio_off

c3_suspend
        bsr c2_publish
        bsr c3_retire
        bsr e3_leave
        lea (c2_clock,pc),a0
        move.l (c2_serial,pc),d0
        bsr world_clock_observe
        moveq #0,d0
        move.w WC_CREDIT(a0),d0
        lea (c3_rebased,pc),a1
        add.l d0,(a1)
        clr.w WC_CREDIT(a0)
        clr.w WC_PHASE(a0)
        clr.w WC_BATCH(a0)
        lea (c3_suspended,pc),a1
        move.w #1,(a1)
        lea (d2_pending,pc),a1
        clr.w (a1)
        lea (c2_in_tick,pc),a1
        clr.w (a1)
        lea (c2_draw_mode,pc),a1
        clr.w (a1)
        lea (c2_scene_ready,pc),a1
        clr.w (a1)
        lea (c3_idle_start,pc),a1
        move.l (c2_clock+WC_LAST,pc),(a1)
        bra c4_flush

c3_resume
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        move.w (c3_suspended,pc),d0
        beq.s .done
        bsr c2_acquire
        move.l (c2_serial,pc),d0
        move.l d0,d1
        sub.l (c3_idle_start,pc),d1
        lea (c3_excluded,pc),a1
        add.l d1,(a1)
        lea (c2_clock,pc),a0
        move.l d0,WC_LAST(a0)
        lea (c2_sound_serial,pc),a1
        move.l d0,(a1)
        movea.l (c2_h0,pc),a1
        move.w ($125a,a1),($125c,a1)
        clr.w ($125e,a1)
        lea (c2_in_tick,pc),a1
        move.w #1,(a1)
        lea (c2_draw_mode,pc),a1
        move.w #1,(a1)          ; resumed tick must paint, even after catch-up
        lea (c3_suspended,pc),a1
        clr.w (a1)
.done
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        rts

; The native accelerated pit/session reconstruction is not a timed world loop.
; Suspend the outer reserved tick, let its native loop run, and resume without debt.
c3_reconstruct
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        move.w (c2_in_tick,pc),d0
        beq.s .ready
        bsr c3_suspend
        lea (c3_reconstructions,pc),a0
        addq.l #1,(a0)
.ready
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        bsr .native
        bra c3_resume
.native
        move.l (c3_native_reconstruct,pc),-(sp)
        rts

c3_replay_enter
        bsr c3_leave_replay_start
        move.l (c3_native_replay_enter,pc),-(sp)
        rts
c3_race_exit
        bsr c3_leave_race
        bra c3_audio_off
c3_audio_off
        move.l (c3_native_audio_off,pc),-(sp)
        rts

; Wait for the last published bitmap to be acknowledged before native ownership.
c3_retire
        movea.l (c2_h2,pc),a2
        adda.l #$1dab0,a2
.pending
        tst.b (a2)
        bne.s .pending
        move.l (c2_serial,pc),d0
.field
        cmp.l (c2_serial,pc),d0
        beq.s .field
        bra c2_drain

; Close an epoch before replay setup, menus/results/loading or a new live entry.
; Retain its accounting and whether native control abandoned a reserved tick.
c3_leave_restart
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        moveq #1,d7
        bra c3_leave
c3_leave_replay_start
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        moveq #2,d7
        bra c3_leave
c3_leave_replay_end
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        moveq #3,d7
        bra c3_leave
c3_leave_race
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        moveq #4,d7
        bra c3_leave
c3_leave
        move.w (c2_mode,pc),d0
        beq.s .done
        bsr c2_hud_flush
        bsr c3_retire
        bsr e3_leave
        IFNE VERIFY
        bsr e3_log_counts
        ENDC
        lea (c2_clock,pc),a0
        move.l (c2_serial,pc),d0
        bsr world_clock_observe
        lea (c3_closed_clock,pc),a1
        moveq #WC_SIZE/4-1,d0
.copy
        move.l (a0)+,(a1)+
        dbf d0,.copy
        move.l (c3_rebased,pc),(a1)+
        move.w (c2_in_tick,pc),(a1)+
        move.w (c2_mode,pc),(a1)+
        move.w d7,(a1)
        lea (c3_inactive,pc),a0
        move.w #1,(a0)
        lea (c3_idle_start,pc),a0
        move.l (c3_closed_clock+WC_LAST,pc),(a0)
        lea (c3_exits,pc),a0
        addq.l #1,(a0)
        lea (c2_mode,pc),a0
        clr.w (a0)
        lea (d2_pending,pc),a0
        clr.w (a0)
        lea (c2_in_tick,pc),a0
        clr.w (a0)
        lea (c2_draw_mode,pc),a0
        clr.w (a0)
        lea (c2_scene_ready,pc),a0
        clr.w (a0)
        bsr c4_flush
.done
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        rts

; C4: a key change stays visible until a native per-tick scan has seen it.
; Between two scans, a press and release would otherwise be lost in the native
; key table h2+$52A, which holds only the current state. Deferral is live from a
; scan until the loop suspends, pauses or leaves; those paths flush to the
; physical state, so native loops without tick scans never see a held-over key.
C4_PHYS = 0                     ; key physically down
C4_FRESH = 1                    ; shown state not yet seen by a scan
C4_UP = 2                       ; release waits for the next scan
C4_DOWN = 3                     ; press waits for the next scan

; Keyboard interrupt, after the native decode: D0 is the key code and A0 the
; native key table. D0=$FF makes the native handler skip its table store.
c4_key
        cmpi.b #$f0,d0
        bcc.s .exit
        movem.l d1-d3/a1,-(sp)
        moveq #$7f,d1
        and.w d0,d1
        lea (c4_keys,pc),a1
        adda.w d1,a1
        move.b (a1),d2
        bclr #C4_PHYS,d2
        tst.b d0
        bmi.s .phys
        bset #C4_PHYS,d2
.phys
        move.w (c4_live,pc),d3
        beq.s .native
        tst.b (0,a0,d1.w)
        sne d3                  ; shown down
        tst.b d0
        bmi.s .release
        tst.b d3
        bne.s .press_shown
        btst #C4_FRESH,d2
        bne.s .defer_down       ; the release has not been seen yet
        bset #C4_FRESH,d2
        bra.s .native
.press_shown
        btst #C4_UP,d2
        beq.s .native
.defer_down
        bset #C4_DOWN,d2
        bra.s .skip
.release
        tst.b d3
        beq.s .release_hidden
        btst #C4_FRESH,d2
        bne.s .defer_up         ; the press has not been seen yet
        bset #C4_FRESH,d2
        bra.s .native
.defer_up
        bset #C4_UP,d2
        bra.s .skip
.release_hidden
        btst #C4_DOWN,d2
        beq.s .native
.skip
        move.b d2,(a1)
        lea (c4_deferred,pc),a1
        addq.l #1,(a1)
        movem.l (sp)+,d1-d3/a1
        moveq #-1,d0
        rts
.native
        move.b d2,(a1)
        movem.l (sp)+,d1-d3/a1
.exit
        rts

; Replaces the live and replay JSRs to the native key scan h0+$64. The scan
; that follows sees the current state; a deferred change is applied only after
; a scan has seen the state before it, so each press lasts one whole tick.
c4_scan
        movem.l d0-d3/a0-a1,-(sp)
        move.w $dff01c,d3
        move.w #$0008,$dff09a   ; keyboard interrupt off while the table changes
        movea.l (c2_h2,pc),a0
        adda.w #$52a,a0
        lea (c4_keys,pc),a1
        moveq #0,d0
        moveq #127,d1
.key
        move.b (a1),d2
        bclr #C4_FRESH,d2
        bne.s .next
        bclr #C4_UP,d2
        beq.s .down
        clr.b (a0)
        addq.l #1,d0
        bra.s .next
.down
        bclr #C4_DOWN,d2
        beq.s .next
        move.b #$b3,(a0)
        addq.l #1,d0
        btst #C4_PHYS,d2
        bne.s .next
        bset #C4_UP,d2          ; a tap: release after this press is seen
.next
        move.b d2,(a1)+
        addq.l #1,a0
        dbf d1,.key
        lea (c4_applied,pc),a1
        add.l d0,(a1)
        lea (c4_live,pc),a1
        move.w #1,(a1)
        btst #3,d3
        beq.s .masked
        move.w #$8008,$dff09a
.masked
        movem.l (sp)+,d0-d3/a0-a1
        move.l (c2_h0,pc),-(sp)
        addi.l #$64,(sp)
        rts

; Leave the deferral: show every key as it physically is.
c4_flush
        movem.l d1-d3/a0-a1,-(sp)
        move.w $dff01c,d3
        move.w #$0008,$dff09a
        lea (c4_live,pc),a1
        clr.w (a1)
        movea.l (c2_h2,pc),a0
        adda.w #$52a,a0
        lea (c4_keys,pc),a1
        moveq #127,d1
.key
        move.b (a1),d2
        andi.b #(1<<C4_UP)|(1<<C4_DOWN),d2
        beq.s .next
        clr.b (a0)
        btst #C4_PHYS,(a1)
        beq.s .next
        move.b #$b3,(a0)
.next
        andi.b #1<<C4_PHYS,(a1)+
        addq.l #1,a0
        dbf d1,.key
        btst #3,d3
        beq.s .masked
        move.w #$8008,$dff09a
.masked
        movem.l (sp)+,d1-d3/a0-a1
        rts

        CNOP 0,4
c3_epochs dc.l 0
c3_exits dc.l 0
c3_pauses dc.l 0
c3_reconstructions dc.l 0
c3_rebased dc.l 0
c3_excluded dc.l 0
c3_idle_start dc.l 0
c3_closed_clock ds.b WC_SIZE+10
c3_inactive dc.w 0
c3_suspended dc.w 0

; Observe one complete beam sweep, after synchronising to its wrap. PAL has
; lines beyond 280; NTSC wraps near 262. Read VPOSR/VHPOSR together and discard
; horizontal position and chip ID/LOF bits. No timer, interrupt or display write.
; D1 returns the nominal field rate; startup observation precedes the epoch.
c2_field_rate
        bsr.s c2_beam_line
        move.w d3,d2
.sync
        bsr.s c2_beam_line
        cmp.w d2,d3
        bcs.s .start
        move.w d3,d2
        bra.s .sync
.start
        move.w d3,d2
        move.w d3,d1
.sample
        bsr.s c2_beam_line
        cmp.w d2,d3
        bcs.s .done
        move.w d3,d2
        cmp.w d1,d3
        bls.s .sample
        move.w d3,d1
        bra.s .sample
.done
        lea (c2_beam_max,pc),a1
        move.w d1,(a1)
        cmpi.w #280,d1
        bcs.s .ntsc
        moveq #50,d1
        rts
.ntsc
        moveq #60,d1
        rts

; A long custom-register read uses two bus cycles. Recheck VP8 so a read
; crossing line 255/256 cannot masquerade as field wrap.
c2_beam_line
.retry
        move.l $dff004,d3
        lsr.l #8,d3
        andi.w #$1ff,d3
        move.w $dff004,d4
        lsl.w #8,d4
        eor.w d3,d4
        btst #8,d4
        bne.s .retry
        rts

; A5: complete old publication, cross the following VBL, then acquire old front.
c2_acquire
        move.l (e3_buffer,pc),d0
        bne e3_acquire
        movea.l (c2_h2,pc),a2
        adda.l #$1dab0,a2
.pending
        tst.b (a2)
        bne.s .pending
        move.l (c2_serial,pc),d0
.vbl
        cmp.l (c2_serial,pc),d0
        beq.s .vbl
        bsr d2_shown
        bsr c2_drain
        movea.l (c2_h0,pc),a2
        adda.l #$124a,a2
        movea.l 4(a2),a3       ; acknowledged front
        move.l (a2),d0
        cmp.l a3,d0
        bne.s .back
        movea.l (c2_h2,pc),a4
        adda.l #$231da,a4
        exg a0,a4
        bsr e4_map
        exg a0,a4
        add.l (a4),d0
.back
        move.l d0,8(a2)
        move.l d0,12(a2)
        move.l d0,a4
        ; Carry persistent HUD pixels into the owned buffer. Optimise only later.
        move.w #7999,d0
.copy
        move.l (a3)+,(a4)+
        dbf d0,.copy
        btst #1,(preference_options+3,pc)
        beq.s .ready
        move.l (c2_serial,pc),d1
.delay
        move.l (c2_serial,pc),d0
        sub.l d1,d0
        cmpi.l #20,d0
        bcs.s .delay
.ready
        rts

c2_drain
        movea.l (c2_h2,pc),a2
        adda.l #$1e2de,a2
.queue
        move.w (a2),d0
        cmp.w 2(a2),d0
        bne.s .queue
        btst #6,$dff002
.busy
        btst #6,$dff002
        bne.s .busy
        rts

c2_pacer
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        move.w (c2_in_tick,pc),d0
        beq.s .native
        btst #3,(cache_options+3,pc)
        beq.s .count
        bsr d1_snapshot
.count
        lea (c2_clock,pc),a0
        addq.l #1,WC_TICKS(a0)
        movea.l (c2_h0,pc),a2
        adda.l #$1260,a2
        addq.w #1,(a2)         ; native frame-indexed state now counts whole ticks
        lea (c2_in_tick,pc),a1
        clr.w (a1)
        move.w (c2_draw_mode,pc),d0
        cmpi.w #2,d0
        beq.s .done
        bsr c2_publish
        lea (c2_clock,pc),a0
        clr.w WC_BATCH(a0)
.done
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        rts
.native
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        move.l a0,-(sp)
        movea.l (c2_h0,pc),a0
        adda.l #$125a,a0
        move.w 4(a0),2(a0)
        movea.l (sp)+,a0
        move.l (c2_pacer_rest,pc),-(sp)
        rts
; D1: at each completed tick, before the pacer counts it, record the native
; renderer inputs mapped by A4 with the field number. Two buffers alternate, so
; cur is the tick just completed and prev the one before. Read-only for the game.
D1_RECORD = 76                  ; d1_fields per record
D1_HEADER = 24
D1_RANGES = 158                 ; d1_ranges bytes
D1_SIZE = D1_HEADER+D1_RANGES+27*D1_RECORD
d1_record                       ; A4 record base, A1 destination
        lea (d1_fields,pc),a2
.field
        move.w (a2)+,d0
        bmi.s .end
        lea (a4,d0.w),a0
        move.w (a2)+,d1
.copy
        move.w (a0)+,(a1)+
        dbf d1,.copy
        bra.s .field
.end
        rts
d1_snapshot
        lea (d1_current,pc),a0
        eori.w #1,(a0)
        lea (d1_buffers,pc),a1
        tst.w (a0)
        beq.s .header
        adda.w #D1_SIZE,a1
.header
        move.l (c2_serial,pc),(a1)+
        move.l (c2_clock+WC_TICKS,pc),d0
        addq.l #1,d0
        move.l d0,(a1)+
        move.l (c3_epochs,pc),(a1)+
        move.l (c3_rebased,pc),(a1)+
        move.l (c3_reconstructions,pc),(a1)+
        move.w (c2_mode,pc),(a1)+
        move.w (c2_draw_mode,pc),(a1)+
        lea (d1_ranges,pc),a2
.range
        move.w (a2)+,d0         ; hunk*4, or -1
        bmi.s .records
        lea (c2_h0,pc),a0
        movea.l (a0,d0.w),a0
        adda.l (a2)+,a0
        bsr e4_map
        move.w (a2)+,d0
.word
        move.w (a0)+,(a1)+
        dbf d0,.word
        bra.s .range
.records
        movea.l (c2_h1,pc),a3
        lea ($256,a3),a4        ; synthetic camera
        bsr.s d1_record
        lea ($5d6,a3),a4
        moveq #25,d2
.car
        bsr.s d1_record
        lea ($c0,a4),a4
        dbf d2,.car
        IFNE VERIFY
        bsr d3_tick_check
        ENDC
d1_done
        rts
; Hunk*4, offset, words-1: view state, chase/player, published camera,
; yaw coefficients, TV/chase parameters, horizon and viewport, covered-road flag.
d1_ranges
        dc.w 4
        dc.l $224
        dc.w 15
        dc.w 0
        dc.l $3a70c
        dc.w 11
        dc.w 0
        dc.l $3a7f8
        dc.w 25
        dc.w 0
        dc.l $3a8c2
        dc.w 1
        dc.w 0
        dc.l $3a8f8
        dc.w 11
        dc.w 8
        dc.l $231d4
        dc.w 9
        dc.w 8
        dc.l $231a0
        dc.w 0
        dc.w -1
; Record offset, words-1: pose, track position, velocity and identity bits;
; steering and correction; list index; speed change; pose flag and packed lap;
; height offset; status; driver; cockpit pitch effect.
d1_fields
        dc.w $00,27
        dc.w $48,1
        dc.w $66,0
        dc.w $72,0
        dc.w $7e,1
        dc.w $8c,0
        dc.w $96,0
        dc.w $ac,0
        dc.w $b6,0
        dc.w -1

; D2: presentation phase of the picture about to be drawn, unsigned Q14 of the
; next tick interval, 0 to 2 ticks: the fields since the current tick fell due (its remaining credit
; plus fields not yet observed) and the lead the previous picture of the same kind
; took from its start to its first displayed field. When pictures are longer than
; the two-tick horizon (that lead, or the period since the last picture started,
; exceeds twice the next interval) the picture shows the latest state: alpha 0. A
; single picture just over a tick still predicts (D9). Read-only for the game.
D2_TICK = 0                     ; drawn inside a tick, from the new state
D2_REPEAT = 2                   ; drawn between ticks
d2_picture                      ; D0 = kind
        btst #3,(cache_options+3,pc)
        beq d2_off
        movem.l d0-d3/a0-a1,-(sp)
        lea (d2_kind,pc),a1
        move.w d0,(a1)
        move.w #1,d2_pending-d2_kind(a1)
        addq.l #1,d2_pictures-d2_kind(a1)
        lea (d2_leads,pc),a0
        move.w (a0,d0.w),d3     ; lead, 0 before the first measurement
        move.w d3,d2_lead-d2_kind(a1)
        move.l (c2_serial,pc),d1
        move.l d1,d2
        sub.l d2_start-d2_kind(a1),d2
        cmpi.l #$7fff,d2
        bls.s .period
        move.w #$7fff,d2
.period
        move.w d2,d2_period-d2_kind(a1)
        move.l d1,d2_start-d2_kind(a1)
        lea (c2_clock,pc),a0
        sub.l WC_LAST(a0),d1
        add.w WC_CREDIT(a0),d1
        move.w d1,d2_phase-d2_kind(a1)
        bsr world_clock_interval
        move.w d0,d2_interval-d2_kind(a1)
        cmp.w d2_period-d2_kind(a1),d3
        bcc.s .longest
        move.w d2_period-d2_kind(a1),d3
.longest
        moveq #0,d2
        cmp.w d0,d3
        bls.s .predict
        sub.w d0,d3             ; D9: latest only beyond the two-tick horizon
        cmp.w d0,d3
        bls.s .predict
        addq.l #1,d2_latest-d2_kind(a1)
        bra.s d2_done
.predict
        move.w d2_lead-d2_kind(a1),d3
        add.w d3,d1
        move.w d0,d3
        add.w d3,d3             ; at most two ticks ahead
        move.w #$8000,d2
        cmp.w d3,d1
        bcc.s d2_done
        moveq #0,d2
        move.w d1,d2
        lsl.l #8,d2
        lsl.l #6,d2
        divu.w d0,d2
d2_done
        move.w d2,d2_alpha-d2_kind(a1)
        ; D10: the history's weight. A picture interpolates between the history and
        ; cur, shown a tick plus the longer of the two measured leads late, so that
        ; even a picture displayed at the end of a tick still interpolates: fraction
        ; (fields since the tick fell due + lead - longest lead) / interval.
        moveq #0,d3             ; alpha 0 or a tick or more: cur
        tst.w d2
        beq.s .weighed
        lea (d2_leads,pc),a0
        move.w (a0)+,d2
        cmp.w (a0),d2
        bcc.s .longer
        move.w (a0),d2
.longer
        sub.w d2,d1
        bmi.s .history
        cmp.w d0,d1
        bcc.s .weighed
        moveq #0,d2
        move.w d1,d2
        lsl.l #8,d2
        lsl.l #6,d2
        divu.w d0,d2
        move.w #$4000,d3
        sub.w d2,d3
        bra.s .weighed
.history
        move.w #$4000,d3
.weighed
        move.w d3,d2_weight-d2_kind(a1)
        movem.l (sp)+,d0-d3/a0-a1
d2_off
        rts
; In c2_acquire, at the first field after the copper took the bitmap.
d2_shown
        lea (d2_pending,pc),a2
        tst.w (a2)
        beq.s .done
        clr.w (a2)
        move.l (c2_serial,pc),d0
        sub.l (d2_start,pc),d0
        cmpi.l #$7fff,d0
        bls.s .store
        move.w #$7fff,d0
.store
        lea (d2_leads,pc),a2
        adda.w (d2_kind,pc),a2
        move.w d0,(a2)
.done
        rts

; D3: just before a picture is drawn, write the renderer inputs it shows into the
; game (staged) and keep the authoritative bytes (saved); write those back right
; after the draw, before any simulation code. The staged set is the pose subset of
; the D1 layout; flags, pointers to records, identities and the camera spring stay
; authoritative. D4 predicts the camera and D5 the cars; everything else is
; staged with its authoritative value. The VERIFY probe stages the previous tick instead.
D3_GLOBALS = 56                 ; d3_ranges bytes
D3_SIZE = D3_GLOBALS+27*38
d3_stage                        ; D0 = kind
        btst #3,(cache_options+3,pc)
        beq d3_off
        movem.l d0-a6,-(sp)
        lea (d3_kind,pc),a0
        move.w d0,(a0)
        lea (d3_pictures,pc),a0
        addq.l #1,(a0)
        ; History is the snapshot of the tick before the one drawn: cur inside a
        ; tick (its own snapshot is taken at the pacer), prev between ticks.
        lea (d1_buffers,pc),a3
        move.w (d1_current,pc),d1
        move.l (c2_clock+WC_TICKS,pc),d2
        tst.w d0
        beq.s .tick
        eori.w #1,d1
        subq.l #1,d2
.tick
        tst.w d1
        beq.s .history
        adda.w #D1_SIZE,a3
.history
        moveq #0,d7
        move.w (d2_alpha,pc),d1
        bne.s .valid
        lea (d3_latest,pc),a0
        addq.l #1,(a0)
        bra.s .debris
.valid
        cmp.l 4(a3),d2
        bne.s .snap
        move.l 8(a3),d1
        cmp.l (c3_epochs,pc),d1
        bne.s .snap
        move.w 20(a3),d1
        cmp.w (c2_mode,pc),d1
        bne.s .snap
        movea.l (c2_h1,pc),a0
        move.l ($234,a0),d1
        cmp.l (D1_HEADER+$10,a3),d1
        bne.s .snap
        move.l ($238,a0),d1
        cmp.l (D1_HEADER+$14,a3),d1
        bne.s .snap
        move.b ($23c,a0),d1
        cmp.b (D1_HEADER+$18,a3),d1
        bne.s .snap
        moveq #2,d7             ; predict
        IFNE VERIFY
        btst #1,(verify_options+3,pc)
        beq.s .debris
        moveq #1,d7
        ENDC
        bra.s .debris
.snap
        lea (d3_snapped,pc),a0
        addq.l #1,(a0)
.debris
        ; A3: a drawn car with record +$19 bit 4 starts the debris deadline when
        ; it is zero. Inside a tick that must follow native visibility, so such a
        ; picture is not staged. Between ticks C2 restores the deadline anyway.
        tst.w d0
        bne.s .stage
        movea.l (c2_h0,pc),a0
        adda.l #$3a770,a0
        tst.l (a0)
        bne.s .stage
        movea.l (c2_h1,pc),a0
        lea ($5d6+$19,a0),a0
        moveq #25,d1
.car
        btst #4,(a0)
        bne.s .skip
        lea ($c0,a0),a0
        dbf d1,.car
.stage
        lea (d5_track,pc),a0
        clr.l (a0)
        lea (d3_saved,pc),a2
        lea (d3_copy_game,pc),a5
        bsr d3_walk
        lea (d3_staged,pc),a2
        cmpi.w #1,d7
        bne.s .build
        lea (d3_copy_history,pc),a5
.build
        bsr d3_walk
        cmpi.w #1,d7
        bne.s .camera
        lea (d3_records,pc),a0
        add.l d6,(a0)
        bra.s .load
.camera
        tst.w d7
        beq.s .load
        bsr d4_camera           ; D7 = 0 if the camera jumped; predicts the cars too
.load
        lea (d3_source,pc),a0
        move.w d7,(a0)
        lea (d3_staged,pc),a2
        lea (d3_load,pc),a5
        bsr d3_walk
        move.l (d5_track,pc),d0
        lea (d5_applied,pc),a0
        move.l d0,(a0)
        bsr d5_flags
        lea (d3_staged_pictures,pc),a0
        addq.l #1,(a0)
        lea (d3_active,pc),a0
        move.w #1,(a0)
        bra.s .done
.skip
        lea (d3_debris,pc),a0
        addq.l #1,(a0)
.done
        movem.l (sp)+,d0-a6
d3_off
        rts

d3_restore
        movem.l d0-a6,-(sp)
        lea (d3_active,pc),a0
        tst.w (a0)
        beq.s .done
        clr.w (a0)
        lea (d5_applied,pc),a0
        move.l (a0),d0
        clr.l (a0)
        bsr d5_flags
        lea (d1_buffers,pc),a3
        IFNE VERIFY
        lea (d3_staged,pc),a2
        lea (d3_compare_game,pc),a5
        bsr d3_walk
        tst.w d5
        beq.s .kept
        lea (d3_written,pc),a0
        addq.l #1,(a0)
.kept
        ENDC
        lea (d3_saved,pc),a2
        lea (d3_load,pc),a5
        bsr d3_walk
        IFNE VERIFY
        ; Inside a tick the tick's own snapshot checks the restore at the pacer.
        ; Between ticks nothing has run since the last snapshot: cur must match.
        move.w (d3_kind,pc),d0
        bne.s .repeat
        move.l (c2_clock+WC_TICKS,pc),d0
        addq.l #1,d0
        lea (d3_check_tick,pc),a0
        move.l d0,(a0)
        bra.s .restored
.repeat
        move.w (d1_current,pc),d0
        beq.s .cur
        adda.w #D1_SIZE,a3
.cur
        lea (d3_compare_snapshot,pc),a5
        bsr d3_walk
        bsr d3_count_check
.restored
        ENDC
        bsr d3_restored
.done
        movem.l (sp)+,d0-a6
        rts
d3_restored
        rts

; A5 = operation on one run of words: A0 game, A1 the run in snapshot A3, A2 packed
; buffer (advanced), D1 words-1, D4 nonzero if the record's pose flag differs from
; the snapshot's. Returns D5 nonzero if a comparison differed, D6 such records.
d3_walk
        movem.l d2-d4/a3-a4/a6,-(sp)
        moveq #0,d4
        moveq #0,d5
        moveq #0,d6
        lea (d3_ranges,pc),a6
.range
        move.w (a6)+,d0         ; hunk*4, or -1
        bmi.s .records
        lea (c2_h0,pc),a0
        movea.l (a0,d0.w),a0
        adda.l (a6)+,a0
        bsr e4_map
        move.w (a6)+,d1
        lea (a3),a1
        adda.w (a6)+,a1
        jsr (a5)
        bra.s .range
.records
        movea.l (c2_h1,pc),a4
        lea ($256,a4),a4        ; synthetic camera, then the cars from +$5D6
        lea (D1_HEADER+D1_RANGES,a3),a3
        move.w #$5d6-$256,d3
        moveq #26,d2
.record
        move.b ($7e,a4),d4
        move.b (64,a3),d0
        eor.b d0,d4
        andi.w #1,d4
        add.w d4,d6
        lea (d3_fields,pc),a6
.field
        move.w (a6)+,d0
        bmi.s .next
        lea (a4,d0.w),a0
        move.w (a6)+,d1
        lea (a3),a1
        adda.w (a6)+,a1
        jsr (a5)
        bra.s .field
.next
        adda.w d3,a4
        move.w #$c0,d3
        lea (D1_RECORD,a3),a3
        dbf d2,.record
        movem.l (sp)+,d2-d4/a3-a4/a6
        rts
d3_copy_history
        tst.w d4
        bne.s d3_copy_game
.copy
        move.w (a1)+,(a2)+
        dbf d1,.copy
        rts
d3_copy_game
.copy
        move.w (a0)+,(a2)+
        dbf d1,.copy
        rts
d3_load
.copy
        move.w (a2)+,(a0)+
        dbf d1,.copy
        rts
        IFNE VERIFY
d3_compare_game                 ; buffer against game
.word
        cmpm.w (a0)+,(a2)+
        beq.s .same
        moveq #1,d5
.same
        dbf d1,.word
        rts
d3_compare_snapshot             ; snapshot against game
.word
        cmpm.w (a0)+,(a1)+
        beq.s .same
        moveq #1,d5
.same
        dbf d1,.word
        rts
d3_compare_saved                ; snapshot against buffer
.word
        cmpm.w (a1)+,(a2)+
        beq.s .same
        moveq #1,d5
.same
        dbf d1,.word
        rts
d3_count_check
        lea (d3_checked,pc),a0
        addq.l #1,(a0)
        tst.w d5
        beq.s .ok
        lea (d3_faults,pc),a0
        addq.l #1,(a0)
.ok
        rts
; In d1_snapshot: the in-tick picture's restore against the tick's snapshot.
d3_tick_check
        move.l (d3_check_tick,pc),d7
        beq.s .none
        lea (d3_check_tick,pc),a0
        clr.l (a0)
        lea (d1_buffers,pc),a3
        move.w (d1_current,pc),d1
        beq.s .cur
        adda.w #D1_SIZE,a3
.cur
        lea (d3_saved,pc),a2
        lea (d3_compare_saved,pc),a5
        bsr d3_walk
        move.l (c2_clock+WC_TICKS,pc),d1
        addq.l #1,d1
        cmp.l d1,d7
        beq d3_count_check
        moveq #1,d5             ; not the tick that was drawn
        bra d3_count_check
.none
        rts
        ENDC
; Hunk*4, offset, words-1, offset in a D1 snapshot: renderer track anchor;
; published camera without the spring; yaw coefficients; horizon; viewport;
; covered-road flag (h0+$33FA0: no sky when the anchor's +$26 bit 3 is set).
d3_ranges
        dc.w 4
        dc.l $224
        dc.w 1,D1_HEADER+0
        dc.w 0
        dc.l $3a7f8
        dc.w 19,D1_HEADER+56
        dc.w 0
        dc.l $3a8c2
        dc.w 1,D1_HEADER+108
        dc.w 8
        dc.l $231d4
        dc.w 0,D1_HEADER+136
        dc.w 8
        dc.l $231e0
        dc.w 0,D1_HEADER+148
        dc.w 8
        dc.l $231e4
        dc.w 0,D1_HEADER+152
        dc.w 8
        dc.l $231a0
        dc.w 0,D1_HEADER+156
        dc.w -1
; Record offset, words-1, offset in a D1 record: direction; pitch; height,
; lateral and longitudinal; segment and denominator; yaw, corrected longitudinal
; and fraction; lap segment and world X/Z; steering and correction; height offset.
d3_fields
        dc.w $00,0,0
        dc.w $04,0,4
        dc.w $08,2,8
        dc.w $12,2,$12
        dc.w $1a,2,$1a
        dc.w $26,4,$26
        dc.w $48,1,56
        dc.w $8c,0,68
        dc.w -1

; D4: the camera of a predicted picture is the published camera interpolated
; between the history and cur, cur - (cur - history) * d2_weight (D10):
; direction, pitch, height and yaw as wrapped words, world X/Z as longs. The
; reduced and coarse X/Z follow as in h0+$33F32, the road anchor is found from
; the tick's anchor by the game's own segment search (h0+$26406), and the yaw
; coefficients, horizon, viewport and covered-road flag are recomputed as
; h0+$3409E, +$3404C, +$33F6E and +$33FA0 do (the flag since D6). Lateral offset
; and lap segment stay at the tick. A camera that moved D4_JUMP or more in X or Z in one tick has
; jumped (a reset or a cut): the picture snaps. VERIFY first recomputes the
; derived values from the tick's own camera and counts any difference.
D4_JUMP = $100000
d4_camera                       ; A3 = history snapshot, d3_staged = the game's values
        movem.l d0-d6/a0-a6,-(sp)
        lea (d3_staged,pc),a2
        movea.l (c2_h0,pc),a0
        adda.l #$3a820,a0
        lea (d4_spring,pc),a1
        move.w (a0),(a1)
        IFNE VERIFY
        bsr d4_derive
        lea (d3_staged,pc),a0
        lea (d3_saved,pc),a1
        moveq #D3_GLOBALS/2-1,d1
.same
        cmpm.w (a0)+,(a1)+
        dbne d1,.same
        beq.s .derived
        lea (d4_faults,pc),a0
        addq.l #1,(a0)
.derived
        ENDC
        lea (4,a2),a0           ; staged published camera
        lea (D1_HEADER+56,a3),a1 ; the history's
        moveq #$a,d2
.bound
        move.l (a0,d2.w),d0
        sub.l (a1,d2.w),d0
        bpl.s .positive
        neg.l d0
.positive
        cmpi.l #D4_JUMP,d0
        bcc .jump
        addq.w #4,d2
        cmpi.w #$e,d2
        beq.s .bound
        move.w (d2_weight,pc),d3
        lea (d4_words,pc),a4
.word
        move.w (a4)+,d2
        bmi.s .longs
        move.w (a0,d2.w),d0
        sub.w (a1,d2.w),d0
        ext.l d0
        bsr d4_scale
        add.w d0,(a0,d2.w)
        bra.s .word
.longs
        moveq #$a,d2
.long
        move.l (a0,d2.w),d0
        sub.l (a1,d2.w),d0
        bsr d4_scale
        add.l d0,(a0,d2.w)
        addq.w #4,d2
        cmpi.w #$e,d2
        beq.s .long
        ; The cars, then an external view's camera from its predicted car (D7),
        ; before the coordinates, anchor and derived values follow the camera.
        bsr d5_cars
        bsr d7_aim
        move.l ($a,a0),d0
        asr.l #8,d0
        move.l d0,($18,a0)
        asr.l #3,d0
        move.w d0,(4,a0)
        move.l ($e,a0),d0
        asr.l #8,d0
        move.l d0,($20,a0)
        asr.l #3,d0
        move.w d0,(8,a0)
        ; The segment search reads a record's world X/Z at +$28/+$2C.
        lea (d4_position,pc),a4
        move.l ($a,a0),(a4)
        move.l ($e,a0),4(a4)
        lea (-$28,a4),a0
        movea.l (a2),a6
        movea.l (c2_h0,pc),a5
        adda.l #$26406,a5
        jsr (a5)
        lea (4,a2),a0
        movea.l (c2_h1,pc),a5
        adda.l #$53de,a5
        cmpa.l a5,a6
        blt.s .held             ; native publication would convert a pit segment
        cmpa.l (a2),a6
        beq.s .anchored
        move.l a6,(a2)
        lea (d4_anchors,pc),a4
        addq.l #1,(a4)
.anchored
        move.w (a6),($26,a0)
        bra.s .derive
.held
        lea (d4_held,pc),a4
        addq.l #1,(a4)
.derive
        bsr d4_derive
        lea (d4_predicted,pc),a4
        addq.l #1,(a4)
        bra.s .done
.jump
        lea (d4_jumps,pc),a4
        addq.l #1,(a4)
        moveq #0,d7
.done
        movem.l (sp)+,d0-d6/a0-a6
        rts
; Offsets in the published camera: direction, pitch, height, yaw.
d4_words
        dc.w 0,2,6,$14,-1
; -(D0.l * D3.w >> 14), the magnitude rounded towards zero, for |D0| < 2^20: with
; D0 = cur - history and D3 = d2_weight, the step back from cur.
d4_scale
        tst.l d0
        bpl.s .negative
        neg.l d0
        bra.s .positive
.negative
        bsr.s .positive
        neg.l d0
        rts
.positive
        move.l d0,d1
        swap d1
        mulu.w d3,d1
        lsl.l #2,d1
        mulu.w d3,d0
        lsr.l #7,d0
        lsr.l #7,d0
        add.l d1,d0
        rts
; A2 = packed stage globals: yaw coefficients, horizon and viewport from the
; published yaw, pitch and anchor heading, the spring and the horizon limit; the
; covered-road flag from the anchor, as h0+$33FA0 does.
d4_derive
        movem.l d0-d1/a0-a1/a4,-(sp)
        movea.l (c2_h0,pc),a4
        adda.l #$222f0,a4
        move.w (4+$14,a2),d0
        bsr d4_table
        move.w d0,(44,a2)
        move.w (4+$14,a2),d0
        neg.w d0
        addi.w #$4000,d0
        bsr d4_table
        move.w d0,(46,a2)
        move.w (4+2,a2),d0
        movea.l (c2_h1,pc),a0
        tst.b ($23c,a0)
        bne.s .pitch
        add.w (d4_spring,pc),d0
.pitch
        neg.w d0
        addi.w #$4000,d0
        bsr d4_table
        asr.w #6,d0
        addi.w #$50,d0
        movea.l (c2_h2,pc),a1
        adda.l #$231cc,a1
        exg a0,a1
        bsr e4_map
        exg a0,a1
        cmp.w (a1),d0
        ble.s .horizon
        move.w (a1),d0
.horizon
        move.w d0,(48,a2)
        clr.w (50,a2)
        move.w (4+$26,a2),d0
        sub.w (4+$14,a2),d0
        bpl.s .relative
        neg.w d0
.relative
        cmpi.w #$4000,d0
        bcs.s .viewport
        neg.w d0
        addi.w #$8000,d0
        move.w #$8000,(50,a2)
.viewport
        move.w d0,(52,a2)
        movea.l (a2),a0
        clr.b (54,a2)
        btst #3,($26,a0)
        beq.s .open
        move.b #$80,(54,a2)
.open
        movem.l (sp)+,d0-d1/a0-a1/a4
        rts
d4_table                        ; D0 = angle, A4 = h0+$222F0
        tst.w d0
        bpl.s .positive
        neg.w d0
.positive
        lsr.w #2,d0
        bclr #0,d0
        move.w (a4,d0.w),d0
        rts

; D5: the cars of a predicted picture, interpolated per record like the camera.
; A track-driven car advances along its segments: progress is its fraction (+$1E,
; Q14) plus $4000 per segment stepped from the history's segment to cur's, and the
; interpolated progress is placed by stepping again from the history's segment,
; the corrected longitudinal (+$1C) following from the fraction with cur's
; denominator (+$16). An explicit car's world X/Z are interpolated and its segment
; found by the game's own search (h0+$26406). Both interpolate pitch, height,
; lateral, yaw, correction and height offset as words; each pose accessor branch reads its own subset. A car
; whose pose flag changed (the game switches it at collisions) advances along its
; segments too, since explicit cars keep their track coordinates, and is drawn
; track-driven: d5_track marks it and d5_flags flips +$7E bit 0 around the draw. A car
; whose status (+$96) changed, that jumped, that crosses a pit transition or more
; than D5_STEPS segments in a tick, or that would stand before its segment (on the
; grid) keeps the tick's pose.
D5_STEPS = 3                    ; segments a car may cross in a tick (2 at most seen)
d5_cars                         ; A3 = history snapshot
        movem.l d0-a6,-(sp)
        move.w (d2_weight,pc),d3
        movea.l (c2_h1,pc),a4
        lea ($5d6,a4),a4        ; the game's record
        lea (D1_HEADER+D1_RANGES+D1_RECORD,a3),a3 ; the history's (after the synthetic camera)
        lea (d3_staged+D3_GLOBALS+38,pc),a2 ; the staged
        moveq #25,d7
.car
        move.b ($7e,a4),d6
        move.b (64,a3),d1
        eor.b d1,d6
        andi.w #1,d6            ; the pose flag changed: along the track
        move.w ($96,a4),d0
        cmp.w (70,a3),d0
        bne .hold
        tst.w d6
        bne.s .track
        btst #0,($7e,a4)
        bne .explicit
.track
        movea.l ($12,a3),a6     ; walk from the history's segment to cur's
        moveq #0,d2
        moveq #D5_STEPS,d5
.walk
        cmpa.l (10,a2),a6
        beq.s .walked
        subq.w #1,d5
        bmi .hold
        bsr d5_step
        bne .hold
        addi.l #$4000,d2
        bra.s .walk
.walked
        move.w (20,a2),d0       ; signed: a grid car can stand before its segment
        ext.l d0
        add.l d0,d2
        move.w ($1e,a3),d0
        ext.l d0
        sub.l d0,d2             ; the progress from the history to cur
        move.l d2,d0
        bsr d4_scale
        add.l d0,d2
        move.w ($1e,a3),d0
        ext.l d0
        add.l d0,d2             ; from the start of the history's segment
        bmi .hold
        movea.l ($12,a3),a6
        moveq #D5_STEPS*2,d5
.ahead
        cmpi.l #$4000,d2
        bcs.s .placed
        subq.w #1,d5
        bmi .hold
        bsr d5_step
        bne.s .stop
        subi.l #$4000,d2
        bra.s .ahead
.stop                           ; D9: stop at the end of the segment before a pit change
        lea (-$2e,a6),a6
        move.l #$3fff,d2
.placed
        cmpa.l (10,a2),a6
        beq.s .segment
        move.l a6,(10,a2)
        lea (d5_moved,pc),a0
        addq.l #1,(a0)
.segment
        move.w d2,(20,a2)
        subi.w #$4000,d2
        muls.w (14,a2),d2
        asl.l #2,d2
        swap d2
        addi.w #$400,d2
        move.w d2,(18,a2)
        tst.w d6
        beq .words
        moveq #25,d0
        sub.w d7,d0
        move.l (d5_track,pc),d1
        bset d0,d1
        lea (d5_track,pc),a0
        move.l d1,(a0)
        bra .words
.explicit
        moveq #24,d2
.bound
        move.l (a2,d2.w),d0
        sub.l ($28-24,a3,d2.w),d0
        bpl.s .positive
        neg.l d0
.positive
        cmpi.l #D4_JUMP,d0
        bcc .hold
        addq.w #4,d2
        cmpi.w #28,d2
        beq.s .bound
        lea (d4_position,pc),a0 ; the segment search reads +$28/+$2C
        moveq #24,d2
.long
        move.l (a2,d2.w),d0
        sub.l ($28-24,a3,d2.w),d0
        bsr d4_scale
        add.l (a2,d2.w),d0
        move.l d0,(a2,d2.w)
        move.l d0,(-24,a0,d2.w)
        addq.w #4,d2
        cmpi.w #28,d2
        beq.s .long
        lea (-$28,a0),a0
        movea.l (10,a2),a6
        movea.l (c2_h0,pc),a1
        adda.l #$26406,a1
        jsr (a1)
        cmpa.l (10,a2),a6
        beq.s .words
        move.l a6,(10,a2)
        lea (d5_moved,pc),a0
        addq.l #1,(a0)
.words
        lea (d5_words,pc),a0
.word
        move.w (a0)+,d2
        bmi.s .predicted
        move.w (a0)+,d4
        move.w (a2,d2.w),d0
        sub.w (a3,d4.w),d0
        ext.l d0
        bsr d4_scale
        add.w d0,(a2,d2.w)
        bra.s .word
.predicted
        lea (d5_predicted,pc),a0
        addq.l #1,(a0)
        bra.s .next
.hold
        lea (d5_held,pc),a0
        addq.l #1,(a0)
.next
        lea (38,a2),a2
        lea (D1_RECORD,a3),a3
        lea ($c0,a4),a4
        dbf d7,.car
        movem.l (sp)+,d0-a6
        rts
; D10: the pit-stop sprites $AA, $A9 and $AE (the block at h2+$2A2A8, for the viewed
; car's +$97 bits 3-5) slide sideways: h2+$2A0FA, +$2A19E and +$2A226 advance the
; pit-service counters (A3 tick state) and return the sprite's x in D4. Each call
; is hooked: the native routine runs unchanged, its x is kept per tick, and an
; interpolated picture shows x interpolated between the history's tick and cur's.
d10_pit_a
        move.l #$2a0fa,-(sp)
        clr.w -(sp)
        bra.s d10_pit
d10_pit_b
        move.l #$2a19e,-(sp)
        move.w #D10_PIT,-(sp)
        bra.s d10_pit
d10_pit_c
        move.l #$2a226,-(sp)
        move.w #2*D10_PIT,-(sp)
d10_pit                         ; (SP).w = entry, 2(SP).l = the routine's h2 offset
        move.l a1,-(sp)
        movea.l (c2_h2,pc),a1
        adda.l (6,sp),a1
        jsr (a1)                ; A0 = the car record; D4 = x
        movea.l (sp)+,a1
        movem.l d0-d3/a0,-(sp)
        btst #3,(cache_options+3,pc)
        beq.s .done
        lea (d10_pits,pc),a0
        adda.w (20,sp),a0
        move.l (c2_clock+WC_TICKS,pc),d1
        move.w (d3_kind,pc),d3
        bne.s .drawn
        addq.l #1,d1            ; inside a tick: the new tick
.drawn
        move.l (c3_epochs,pc),d2
        cmp.l (a0),d2
        bne.s .first
        move.l 4(a0),d3
        cmp.l d3,d1
        beq.s .kept
        addq.l #1,d3
        cmp.l d3,d1
        bne.s .first
        move.w 8(a0),10(a0)     ; the previous tick's x
        move.w #1,12(a0)
        bra.s .keep
.first
        clr.w 12(a0)
.keep
        move.l d2,(a0)
        move.l d1,4(a0)
        move.w d4,8(a0)
.kept
        move.w (d3_active,pc),d3
        beq.s .done
        move.w (d3_source,pc),d3
        subq.w #2,d3
        bne.s .done
        tst.w 12(a0)
        beq.s .done
        move.w 8(a0),d0
        sub.w 10(a0),d0
        ext.l d0
        move.w (d2_weight,pc),d3
        bsr d4_scale
        move.w 8(a0),d4
        add.w d0,d4
.done
        movem.l (sp)+,d0-d3/a0
        addq.l #6,sp
        rts
D10_PIT = 14                    ; epoch.l, tick.l, x.w, previous x.w, previous valid.w

; D7: an external view's camera from the staged viewed car (h1+$238), placed and
; aimed as the native view code does in the tick. Chase (view bit 5, h0+$398AA):
; the camera stands h0+$3A90C from the car along the chase heading h0+$3A710,
; turned by $8000 in front chase (bit 4); the heading is interpolated like the
; camera words. TV (h0+$39BD0): the camera stays where D4 put it. Both aim the
; direction and yaw at the car with the game's atan h0+$256B6 (h0+$39CBE). The
; cockpit views, whose camera is the car itself, and a TV camera on a track point
; (h1+$240 nonzero) keep D4's camera. VERIFY first places the tick's camera from
; the game's car and heading and counts a difference from the game's.
d7_aim                          ; A3 = history snapshot, d3_staged with predicted cars
        movem.l d0-a6,-(sp)
        movea.l (c2_h1,pc),a5
        lea ($256,a5),a0
        cmpa.l ($234,a5),a0
        bne .done
        btst #5,($23c,a5)
        bne.s .external
        tst.w ($240,a5)
        bne .done
.external
        movea.l (c2_h0,pc),a4
        adda.l #$3a710,a4
        move.w (a4),d6          ; chase heading at the tick
        IFNE VERIFY
        movea.l ($238,a5),a0
        movea.l ($12,a0),a6
        lea (d3_saved+4,pc),a1
        bsr d7_place
        cmp.l ($a,a1),d0
        bne.s .fault
        cmp.l ($e,a1),d1
        bne.s .fault
        cmp.w ($14,a1),d2
        bne.s .fault
        cmp.w (a1),d2
        beq.s .placed
.fault
        lea (d7_faults,pc),a0
        addq.l #1,(a0)
.placed
        ENDC
        move.w d6,d0
        sub.w (D1_HEADER+36,a3),d0 ; the history's chase heading
        ext.l d0
        move.w (d2_weight,pc),d3
        bsr d4_scale
        add.w d0,d6
        ; The staged car as a record for the pose accessor.
        move.l ($238,a5),d0
        sub.l a5,d0
        subi.l #$5d6,d0
        divu.w #$c0,d0
        move.l (d5_track,pc),d5
        btst d0,d5
        sne d5                  ; drawn in the other representation (D5)
        mulu.w #38,d0
        lea (d3_staged+D3_GLOBALS+38,pc),a2
        adda.w d0,a2
        movea.l ($238,a5),a1
        lea (d7_record,pc),a0
        move.b ($7e,a1),($7e,a0)
        tst.b d5
        beq.s .flag
        bchg #0,($7e,a0)
.flag
        move.w (6,a2),($a,a0)
        move.w (18,a2),($1c,a0)
        move.l (24,a2),($28,a0)
        move.l (28,a2),($2c,a0)
        movea.l (10,a2),a6
        lea (d3_staged+4,pc),a1
        bsr d7_place
        move.l d0,($a,a1)
        move.l d1,($e,a1)
        move.w d2,(a1)
        move.w d2,($14,a1)
        lea (d7_aimed,pc),a0
        addq.l #1,(a0)
.done
        movem.l (sp)+,d0-a6
        rts
; A0 = record, A6 = its segment, D6 = chase heading, A1 = published camera
; -> D0/D1 camera X/Z, D2 its yaw. The accessor's scratch word h0+$25644 is kept.
d7_place
        movem.l d3-d6/a0/a2-a6,-(sp)
        movea.l (c2_h0,pc),a5
        adda.l #$25644,a5
        move.w (a5),-(sp)
        move.l a1,-(sp)
        movea.l (c2_h0,pc),a1
        adda.l #$26272,a1
        jsr (a1)                ; D4/D5 = the car's world X/Z
        movea.l (sp)+,a1
        move.w (sp)+,(a5)
        move.l ($a,a1),d0
        move.l ($e,a1),d1
        movea.l (c2_h1,pc),a2
        btst #5,($23c,a2)
        beq.s .aim
        btst #4,($23c,a2)
        beq.s .rear
        addi.w #$8000,d6
.rear
        movea.l (c2_h0,pc),a4
        adda.l #$222f0,a4
        movea.l (c2_h0,pc),a2
        adda.l #$3a90c,a2       ; chase distance
        move.w d6,d0
        bsr d4_table
        muls.w (a2),d0
        asr.l #6,d0
        move.l d0,d1
        add.l d5,d1
        move.w d6,d0
        neg.w d0
        addi.w #$4000,d0
        bsr d4_table
        muls.w (a2),d0
        asr.l #6,d0
        add.l d4,d0
.aim
        movem.l d0-d1,-(sp)
        sub.l d0,d4
        sub.l d1,d5
        moveq #11,d2
        asr.l d2,d4
        asr.l d2,d5
        move.w d4,d0
        move.w d5,d1
        movea.l (c2_h0,pc),a2
        adda.l #$256b6,a2
        jsr (a2)
        move.w d0,d2
        movem.l (sp)+,d0-d1
        movem.l (sp)+,d3-d6/a0/a2-a6
        rts

; D0 = cars (bit n = car n) drawn in the other representation: flip their +$7E bit 0.
d5_flags
        movem.l d0/a0,-(sp)
        movea.l (c2_h1,pc),a0
        lea ($5d6+$7e,a0),a0
.car
        tst.l d0
        beq.s .done
        lsr.l #1,d0
        bcc.s .next
        bchg #0,(a0)
.next
        lea ($c0,a0),a0
        bra.s .car
.done
        movem.l (sp)+,d0/a0
        rts
; Staged and history offsets: pitch, height, lateral, yaw, correction, height offset.
d5_words
        dc.w 2,$04,4,$08,6,$0a,16,$1a,34,56+2,36,68,-1
; A6 one segment on as the track-driven traversal (h0+$2B402/+2B4AE) steps it
; through h0+$26626, A4 = the game's record: the lap wrap, and the pit branch and
; join points when the car passes them. Returns NE (hold) where h0+$26626 would
; move the car into or out of the pit lane, or with the pit flag h2+$1FABA set.
d5_step
        lea ($2e,a6),a6
        btst #3,($1f,a6)
        beq.s .same
        move.l a0,-(sp)
        movea.l (c2_h2,pc),a0
        adda.l #$1fac2,a0
        cmpa.l (a0),a6
        bne.s .branch
        movea.l (c2_h1,pc),a6
        adda.w #$53de,a6
        bra.s .stepped
.branch
        tst.b ($1faba-$1fac2,a0)
        bmi.s .pit
        cmpa.l ($1fade-$1fac2,a0),a6
        bne.s .join
        btst #7,($23,a4)
        bne.s .pit
        bra.s .stepped
.join
        cmpa.l ($1fad6-$1fac2,a0),a6
        bne.s .stepped
        btst #5,($23,a4)
        bne.s .pit
        movea.l ($1fae2-$1fac2,a0),a6
.stepped
        movea.l (sp)+,a0
.same
        ori.b #4,ccr
        rts
.pit
        movea.l (sp)+,a0
        andi.b #$fb,ccr
        rts

c2_publish
        bsr c2_hud_flush
        bsr c2_drain
        btst #2,(preference_options+3,pc)
        bne.s .no_replay
        move.w (c2_mode,pc),d0
        cmpi.w #2,d0
        bne.s .no_replay
        ; The R is pure painting. Draw once per published replay picture,
        ; including zero-tick pictures, never during intermediate catch-up ticks.
        movem.l d0-a6,-(sp)
        bsr c2_replay_paint
        lea (c2_replay_pictures,pc),a0
        addq.l #1,(a0)
        movem.l (sp)+,d0-a6
.no_replay
        move.w (e3_drawing,pc),d0
        beq.s .chip
        bsr e3_present
.chip
        movea.l (c2_h0,pc),a2
        adda.l #$124e,a2
        move.l 8(a2),(a2)      ; bitmap base, never the external-view viewport
        bsr c2_submit_call
        move.l (e3_buffer,pc),d0
        beq.s .counted
        bsr e3_submitted
.counted
        lea (c2_pictures,pc),a0
        addq.l #1,(a0)
        rts
c2_submit_call
        move.l (c2_submit,pc),-(sp)
        rts
c2_replay_paint
        move.l (c2_native_replay_paint,pc),-(sp)
        rts
c2_replay_tick_paint
        ; Same-build native-painting control; normal enhanced ticks do no R paint.
        move.w sr,-(sp)
        btst #2,(preference_options+3,pc)
        beq.s .deferred
        move.w (sp)+,ccr
        bra.s c2_replay_paint
.deferred
        move.w (sp)+,ccr
        rts

; Replace MOVEA h0+$124A plus its following LEA 32000 with the owned
; bitmap pair during a world tick. Outside the enhanced loop, execute the
; original MOVEA and return to its LEA. Preserve all condition flags.
c2_pair_a0_a2
        move.w sr,-(sp)
        move.w (c2_in_tick,pc),-(sp)
        lea 2(sp),sp
        beq.s .native
        movea.l (c2_h0,pc),a0
        movea.l ($1256,a0),a0
        movea.l a0,a2
        addq.l #4,2(sp)
        bra.s .done
.native
        movea.l (c2_h0,pc),a0
        movea.l ($124a,a0),a0
.done
        move.w (sp)+,ccr
        rts
c2_pair_a5_a6
        move.w sr,-(sp)
        move.w (c2_in_tick,pc),-(sp)
        lea 2(sp),sp
        beq.s .native
        movea.l (c2_h0,pc),a5
        movea.l ($1256,a5),a5
        movea.l a5,a6
        addq.l #4,2(sp)
        bra.s .done
.native
        movea.l (c2_h0,pc),a5
        movea.l ($124a,a5),a5
.done
        move.w (sp)+,ccr
        rts
c2_pair_a1_a2
        move.w sr,-(sp)
        move.w (c2_in_tick,pc),-(sp)
        lea 2(sp),sp
        beq.s .native
        movea.l (c2_h0,pc),a1
        movea.l ($1256,a1),a1
        movea.l a1,a2
        addq.l #4,2(sp)
        bra.s .done
.native
        movea.l (c2_h0,pc),a1
        movea.l ($124a,a1),a1
.done
        move.w (sp)+,ccr
        rts

; C2 CPU HUD display list. Tick code prepares operands and consumes requests;
; only the raster regions are queued. Commands retain register inputs and text
; colours/mode. The bitmap pair remains owned until this list has been painted.
C2_HUD_STRIDE = 96
C2_HUD_CAPACITY = 2048
c2_hud_init
        move.l (c2_h2,pc),d0
        lea (c2_hud_targets,pc),a0
        moveq #11,d1
.loop
        add.l d0,(a0)+
        add.l d0,(a0)+
        add.l d0,(a0)+
        addq.l #4,a0
        dbf d1,.loop
        rts

; D0 is the command index. The caller saved SR and D0-A6; its register
; image starts four bytes above our return address. D0 returns 1 if deferred.
c2_hud_enqueue
        move.w (c2_in_tick,pc),d1
        beq .native
        move.w (c2_hud_replaying,pc),d1
        bne .native
        btst #2,(preference_options+3,pc)
        bne .native
        lea (c2_hud_count,pc),a0
        moveq #0,d1
        move.w (a0),d1
        cmpi.w #C2_HUD_CAPACITY,d1
        bcc c2_hud_overflow
        addq.w #1,(a0)
        lea (c2_hud_high,pc),a1
        move.w (a0),d2
        cmp.w (a1),d2
        bls.s .high
        move.w d2,(a1)
.high
        mulu.w #C2_HUD_STRIDE,d1
        lea (c2_hud_buffer,pc),a1
        adda.l d1,a1
        move.w d0,(a1)+
        move.w d0,d1
        lsl.w #4,d1
        lea (c2_hud_targets,pc),a2
        adda.w d1,a2
        move.w 12(a2),(a1)+
        lea (c2_hud_skip,pc),a0
        move.l 8(a2),(a0)
        lea 4(sp),a0
        moveq #14,d1
.regs
        move.l (a0)+,(a1)+
        dbf d1,.regs
        movea.l (c2_h2,pc),a0
        adda.l #$1f302,a0
        moveq #6,d1
.text
        move.l (a0)+,(a1)+
        dbf d1,.text
        lea (c2_hud_queued,pc),a0
        addq.l #1,(a0)
        cmpi.w #10,d0
        bne.s .not_clear
        lea (c2_background_clears,pc),a0
        addq.l #1,(a0)
.not_clear
        cmpi.w #11,d0
        bne.s .not_copy
        lea (c2_background_copies,pc),a0
        addq.l #1,(a0)
.not_copy
        cmpi.w #1,d0
        beq.s .box
        cmpi.w #2,d0
        bne.s .logged
.box
        bsr c2_box_log
.logged
        ; RPM still walks its packed run list to preserve its register outputs.
        ; Its pixel loop is separately suppressed while preparing the command.
        cmpi.w #8,d0
        beq.s .native
        moveq #1,d0
        rts
.native
        moveq #0,d0
        rts
c2_hud_overflow
        lea (c2_hud_overflows,pc),a0
        addq.l #1,(a0)
        pea (c2_hud_overflow_message,pc)
        pea TDREASON_FAILMSG
        move.l (_resload,pc),a2
        jmp (resload_Abort,a2)

C2_HUD_GATE MACRO
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        moveq #\1,d0
        bsr c2_hud_enqueue
        tst.w d0
        beq.s .native\@
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        IFEQ \1-7
        move.w #-1,d0         ; final DBF value; A0-A2 restored by native epilogue
        ENDC
        IFEQ \1-9
        adda.w d3,a2
        asl.w #2,d3
        adda.w d3,a1
        adda.w #200,a0
        adda.w #200,a2
        adda.w #800,a1
        move.w #-1,d1
        ENDC
        move.l (c2_hud_skip,pc),-(sp)
        rts
.native\@
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        move.l (c2_hud_targets+\1*16+4,pc),-(sp)
        ENDM

c2_hud_icon
        C2_HUD_GATE 0
        adda.l #7370,a0
        rts
c2_hud_box
        C2_HUD_GATE 1
        movea.l (c2_h0,pc),a4
        adda.l #$3ff8a,a4
        rts
c2_hud_copy
        C2_HUD_GATE 2
        adda.w d0,a5
        adda.w d0,a6
        move.w #19,d1
        rts
c2_hud_top
        C2_HUD_GATE 3
        lea 24000(a0),a3
        move.w #79,d0
        rts
c2_hud_digit
        C2_HUD_GATE 4
        movea.l (c2_h0,pc),a3
        adda.l #$3cd32,a3
        rts
c2_hud_image
        C2_HUD_GATE 5
        movea.l (c2_h0,pc),a3
        adda.l #$3cd32,a3
        rts
c2_hud_glyph
        C2_HUD_GATE 6
        asl.l #1,d3
        adda.l d3,a1
        adda.l d3,a2
        rts
c2_hud_gear
        C2_HUD_GATE 7
        adda.w #5832,a0
        adda.w #5832,a2
        rts
c2_hud_rpm
        C2_HUD_GATE 8
        move.l a0,-(sp)
        movea.l (c2_h2,pc),a0
        adda.l #$1f31b,a0
        tst.b (a0)
        movea.l (sp)+,a0
        rts
c2_hud_assist
        C2_HUD_GATE 9
        adda.w d3,a2
        asl.w #2,d3
        adda.w d3,a1
        rts

; Conditional view rebuilds prepare native destinations before these gates.
; Keep the clear/copy in order with the HUD operations from the same tick.
c2_hud_background_clear
        C2_HUD_GATE 10
        move.l a0,d1
        addi.l #32000,d1
        rts
c2_hud_background_copy
        C2_HUD_GATE 11
        muls.w #160,d0
        adda.l d0,a0
        rts

; The packed RPM walker has live register outputs. Skip its stores but retain
; the exact per-run pointer increments, DBF result and subsequent run traversal.
c2_hud_rpm_pixels
        move.w sr,-(sp)
        move.l d0,-(sp)
        move.w (c2_in_tick,pc),d0
        beq.s .native
        move.w (c2_hud_replaying,pc),d0
        bne.s .native
        btst #2,(preference_options+3,pc)
        bne.s .native
        moveq #0,d0
        move.w d5,d0
        addq.l #1,d0
        lsl.l #3,d0
        adda.l d0,a1
        mulu.w #5,d0
        suba.l d0,a0
        suba.l d0,a2
        move.w #-1,d5
        move.l (sp)+,d0
        move.w (sp)+,ccr
        move.l (c2_hud_targets+8*16+8,pc),-(sp)
        rts
.native
        move.l (sp)+,d0
        move.w (sp)+,ccr
        pea 0.w
        move.l a3,-(sp)
        movea.l (c2_h2,pc),a3
        adda.l #$1f9c0,a3
        move.l a3,4(sp)       ; reserve continuation below saved A3
        movea.l (sp)+,a3
        move.w (a1),(a0)+
        move.w (a1)+,(a2)+
        move.w (a1),7998(a0)
        rts

c2_hud_rpm_end
        move.w (c2_hud_replaying,pc),-(sp)
        lea 2(sp),sp
        beq.s .walk
        movea.l (sp)+,a2      ; fake native frame installed by the painter
        rts
.walk
        move.w (a1)+,d5
        beq.s .end
        move.l (c2_hud_targets+8*16,pc),-(sp)
        tst.w d5
        rts
.end
        pea 0.w
        move.l a0,-(sp)
        movea.l (c2_h2,pc),a0
        adda.l #$1f9e6,a0
        move.l a0,4(sp)
        movea.l (sp)+,a0
        tst.w d5
        rts

; Drain at the final scene boundary and before publication. Queued regions
; return through their native epilogues, using disposable saved-register frames.
; Text parser state and UI reuse flags are restored to the authoritative tick.
c2_hud_flush
        move.w sr,-(sp)
        movem.l d0-a6,-(sp)
        lea (c2_hud_count,pc),a0
        tst.w (a0)
        beq .done
        bsr c2_drain
        lea (c2_hud_remaining,pc),a0
        move.w (c2_hud_count,pc),(a0)
        lea (c2_hud_read,pc),a0
        lea (c2_hud_buffer,pc),a1
        move.l a1,(a0)
        lea (c2_hud_saved,pc),a1
        movea.l (c2_h2,pc),a0
        adda.l #$1f302,a0
        moveq #6,d0
.save
        move.l (a0)+,(a1)+
        dbf d0,.save
        movea.l (c2_h2,pc),a0
        adda.l #$231ea,a0
        bsr e4_map
        move.b (a0),(a1)+
        lea (c2_hud_saved_tick,pc),a0
        move.w (c2_in_tick,pc),(a0)
        lea (c2_in_tick,pc),a0
        move.w #1,(a0)
        lea (c2_hud_replaying,pc),a0
        move.w #1,(a0)
.next
        movea.l (c2_hud_read,pc),a1
        moveq #0,d0
        move.w (a1),d0
        lsl.w #4,d0
        lea (c2_hud_targets,pc),a0
        adda.w d0,a0
        lea (c2_hud_target,pc),a2
        move.l (a0),(a2)
        lea 64(a1),a2
        movea.l (c2_h2,pc),a0
        adda.l #$1f302,a0
        moveq #6,d0
.load
        move.l (a2)+,(a0)+
        dbf d0,.load
        lea (.returned,pc),a0
        move.l a0,-(sp)
        suba.w 2(a1),sp
        movem.l 4(a1),d0-a6
        move.l (c2_hud_target,pc),-(sp)
        rts
.returned
        lea (c2_hud_painted,pc),a0
        addq.l #1,(a0)
        lea (c2_hud_read,pc),a0
        add.l #C2_HUD_STRIDE,(a0)
        lea (c2_hud_remaining,pc),a0
        subq.w #1,(a0)
        bne .next
        lea (c2_hud_saved,pc),a1
        movea.l (c2_h2,pc),a0
        adda.l #$1f302,a0
        moveq #6,d0
.restore
        move.l (a1)+,(a0)+
        dbf d0,.restore
        movea.l (c2_h2,pc),a0
        adda.l #$231ea,a0
        bsr e4_map
        move.b (a1)+,(a0)
        lea (c2_in_tick,pc),a0
        move.w (c2_hud_saved_tick,pc),(a0)
        lea (c2_hud_replaying,pc),a0
        clr.w (a0)
        lea (c2_hud_count,pc),a0
        clr.w (a0)
.done
        movem.l (sp)+,d0-a6
        move.w (sp)+,ccr
        rts

; A shown box (Viewing, Riding with, Race won by...) lies over the top of the
; view. Natively the HUD runs after every scene and copies each shown box from
; the front bitmap into the new picture (h2+$1DEF6), so the scene never covers
; it. Here the HUD runs once per tick: log the tick's box draws and copies
; (D0 = 1 or 2, the gate's registers above the two return addresses) as offset and
; copy width, and repeat the copies after the scene of each picture drawn
; between ticks.
C2_BOXES = 16
c2_box_log
        movem.l d1-d2/a0,-(sp)
        move.l (c2_clock+WC_TICKS,pc),d1
        addq.l #1,d1            ; the tick running
        lea (c2_box_tick,pc),a0
        cmp.l (a0),d1
        beq.s .same
        move.l d1,(a0)
        clr.w c2_box_count-c2_box_tick(a0)
.same
        move.w c2_box_count-c2_box_tick(a0),d1
        cmpi.w #C2_BOXES,d1
        bcc.s .full
        addq.w #1,c2_box_count-c2_box_tick(a0)
        lsl.w #2,d1
        lea (c2_boxes,pc),a0
        move.w 22(sp),(a0,d1.w) ; offset (gate D0)
        move.w 30(sp),d2        ; words-1 (gate D2)
        cmpi.w #2,d0
        beq.s .width
        addq.w #2,d2            ; the box draw's D2 is the copy's minus two
.width
        move.w d2,2(a0,d1.w)
.full
        movem.l (sp)+,d1-d2/a0
        rts
c2_repeat_boxes
        movem.l d0-d3/a0-a3,-(sp)
        move.l (c2_box_tick,pc),d0
        cmp.l (c2_clock+WC_TICKS,pc),d0
        bne.s .done             ; the last tick showed no box
        move.w (c2_box_count,pc),d3
        subq.w #1,d3
        bmi.s .done
        lea (c2_boxes,pc),a2
        movea.l (c2_h0,pc),a3
.box
        movea.l ($1256,a3),a0   ; the picture being drawn
        movea.l ($124e,a3),a1   ; the front
        move.w (a2)+,d0
        adda.w d0,a0
        adda.w d0,a1
        move.w (a2)+,d0
        moveq #19,d1
.line
        movem.l a0-a1,-(sp)
        move.w d0,d2
.word
        move.w (a1)+,(a0)+
        move.w $1f3e(a1),$1f3e(a0)
        move.w $3e7e(a1),$3e7e(a0)
        move.w $5dbe(a1),$5dbe(a0)
        dbf d2,.word
        movem.l (sp)+,a0-a1
        lea 40(a0),a0
        lea 40(a1),a1
        dbf d1,.line
        lea (c2_box_repeats,pc),a0
        addq.l #1,(a0)
        dbf d3,.box
.done
        movem.l (sp)+,d0-d3/a0-a3
        rts

        CNOP 0,4
c2_hud_targets
        dc.l $1dd24,$1dd2a,$1ddba ; icon
        dc.w 20,0
        dc.l $1de58,$1de5e,$1dee8 ; box
        dc.w 60,0
        dc.l $1df24,$1df2c,$1df56 ; copy
        dc.w 60,0
        dc.l $1df92,$1df9a,$1dfae ; top
        dc.w 20,0
        dc.l $1ea40,$1ea46,$1ea8a ; digit
        dc.w 60,0
        dc.l $1eb9e,$1eba4,$1ec3a ; image
        dc.w 60,0
        dc.l $1f128,$1f12e,$1f2ae ; glyph
        dc.w 0,0
        dc.l $1f928,$1f930,$1f960 ; gear
        dc.w 12,0
        dc.l $1f974,$1f97a,$1f9e0 ; rpm
        dc.w 4,0
        dc.l $1fa6e,$1fa74,$1faa4 ; assist
        dc.w 0,0
        dc.l $1dc84,$1dc8c,$1dc98 ; full background clear
        dc.w 12,0
        dc.l $1dcbc,$1dcc2,$1dcda ; cockpit background copy
        dc.w 16,0
c2_hud_skip dc.l 0
c2_box_tick dc.l 0
c2_box_repeats dc.l 0           ; boxes copied after a scene between ticks
c2_boxes ds.w 2*C2_BOXES
c2_box_count dc.w 0
c2_hud_target dc.l 0
c2_hud_read dc.l 0
c2_hud_queued dc.l 0
c2_hud_painted dc.l 0
c2_hud_overflows dc.l 0
c2_background_clears dc.l 0
c2_background_copies dc.l 0
c2_hud_count dc.w 0
c2_hud_high dc.w 0
c2_hud_remaining dc.w 0
c2_hud_replaying dc.w 0
c2_hud_saved_tick dc.w 0
c2_hud_saved ds.b 30
c2_hud_overflow_message dc.b 'C2 HUD display list overflow',0
        EVEN

; Geometry/association/mirror traversal still executes on an undrawn tick.
; Only raster leaves are suppressed, preserving the native visibility predicate
; before h2+$29AD8 and the pit/RNG paths at the end of the traversal.
C2_RASTER_GATE MACRO
        move.w sr,-(sp)
        move.w (c2_dry_scene,pc),-(sp)
        lea 2(sp),sp
        beq.s .native\@
        move.w (sp)+,ccr
        rts
.native\@
        move.w (sp)+,ccr
        ENDM

c2_scene
        move.w sr,-(sp)
        move.l d0,-(sp)
        move.w (c2_draw_mode,pc),d0
        cmpi.w #2,d0
        beq.s .keep_hud
        bsr c2_hud_flush
.keep_hud
        move.l (sp)+,d0
        move.w (sp)+,ccr
        movem.l d0-a6,-(sp)
        move.w (c2_draw_mode,pc),d0
        subq.w #1,d0
        bne.s .stage
        moveq #D2_TICK,d0
        bsr d2_picture
        bsr d3_stage
.stage
        lea (c2_stage_entry,pc),a2
        bsr c2_save_stage
        movem.l (sp)+,d0-a6
        move.l a0,-(sp)
        lea (c2_dry_scene,pc),a0
        clr.w (a0)
        move.w (c2_draw_mode,pc),-(sp)
        cmpi.w #2,(sp)+
        bne.s .paint
        btst #2,(preference_options+3,pc)
        bne.s .paint
        move.w #1,(a0)
        lea (c2_dry_passes,pc),a0
        addq.l #1,(a0)
.paint
        movea.l (sp)+,a0
        bsr c2_scene_call
        bsr d3_restore
        move.l a0,-(sp)
        lea (c2_dry_scene,pc),a0
        clr.w (a0)
        lea (c2_scene_ready,pc),a0
        move.w #1,(a0)
        movea.l (sp)+,a0
        rts
c2_scene_call
        move.l (c2_native_scene,pc),-(sp)
        rts

c2_fill
        C2_RASTER_GATE
        move.l a0,-(sp)
        movea.l (c2_h0,pc),a0
        adda.l #$1f37e,a0
        move.w d3,(a0)
        movea.l (sp)+,a0
        move.l (c2_fill_rest,pc),-(sp)
        rts
c2_sprite
        C2_RASTER_GATE
        move.l a0,-(sp)
        movea.l (c2_h0,pc),a0
        move.w d3,($1348,a0)
        movea.l (sp)+,a0
        move.l (c2_sprite_rest,pc),-(sp)
        rts
c2_clear
        C2_RASTER_GATE
        movem.l d0-a6,-(sp)
        bsr c2_colour_call
        IFNE VERIFY
        btst #2,(verify_options+3,pc)
        beq.s .native
        move.w (e3_soft,pc),-(sp)
        tst.w (sp)+
        beq.s .native
        bsr e3_twin_fill
        movem.l (sp)+,d0-a6
        rts
.native
        ENDC
        move.l (c2_clear_rest,pc),-(sp)
        rts
c2_colour_call
        move.l (c2_native_colour,pc),-(sp)
        rts
c2_sky
        C2_RASTER_GATE
        movem.l a0-a3,-(sp)
        clr.w d5
        move.l (c2_sky_rest,pc),-(sp)
        rts
c2_sides
        C2_RASTER_GATE
        movem.l a0-a3,-(sp)
        move.w #7,d6
        move.l (c2_sides_rest,pc),-(sp)
        rts
c2_lights
        C2_RASTER_GATE
        move.l (c2_lights_rest,pc),-(sp)
        move.l a0,-(sp)
        movea.l (c2_h0,pc),a0
        adda.l #$3a73a,a0
        move.w (a0),d7
        movea.l (sp)+,a0
        rts
c2_hands
        C2_RASTER_GATE
        movea.l (c2_h0,pc),a1
        adda.l #$3eb32,a1
        move.l (c2_hands_rest,pc),-(sp)
        rts
c2_blit_queue
        C2_RASTER_GATE
        move.w sr,-(sp)
        move.w (e3_soft,pc),-(sp)
        lea 2(sp),sp
        beq.s .chip
        move.w (sp)+,ccr
        bra e3_queue
.chip
        move.w (sp)+,ccr
        move.l a1,-(sp)
        movea.l (c2_h2,pc),a1
        adda.l #$1e2e4,a1
        move.l (c2_queue_rest,pc),-(sp)
        rts

        CNOP 0,4
c2_target_h0
c2_fill_rest dc.l $1f398
c2_sprite_rest dc.l $1482
c2_native_entry dc.l $3c5c6
c3_native_live_pause dc.l $3b5de
c3_native_replay_pause dc.l $3b80e
c3_native_replay_enter dc.l $39fd2
c3_native_reconstruct dc.l $3ca5a
c2_target_h2
c2_clear_rest dc.l $1e158
c2_native_colour dc.l $1dc50
c2_sky_rest dc.l $1f3c0
c2_sides_rest dc.l $1f56a
c2_lights_rest dc.l $1f782
c2_hands_rest dc.l $1f856
c2_queue_rest dc.l $1e6d4
c2_native_scene dc.l $280f6
c2_native_replay_paint dc.l $1dfb4
c3_native_audio_off dc.l $8e2
c2_target_end
c2_dry_passes dc.l 0
c2_dry_scene dc.w 0

; Between ticks, repaint the last tick's renderer inputs. Renderer-owned tick
; effects are staged from that tick's entry and authoritative post-tick bytes
; restored afterwards. No camera evolution, input or HUD/blink call is repeated.
c2_repeat_picture
        moveq #D2_REPEAT,d0
        bsr d2_picture
        movea.l (c2_h0,pc),a2
        move.l ($1256,a2),d0
        move.l -4(a2),d1      ; next segment BPTR -> hunk 1
        lsl.l #2,d1
        addq.l #4,d1
        movea.l d1,a1
        tst.b ($23c,a1)
        bpl.s .viewport
        addi.l #640,d0
.viewport
        move.l d0,($1252,a2)
        lea (c2_stage_saved,pc),a2
        bsr c2_save_stage
        lea (c2_stage_entry,pc),a2
        bsr c2_load_stage
        moveq #D2_REPEAT,d0
        bsr d3_stage
        ; The renderer skips its blit-queue drain at h2+$27E98 once the native
        ; field counter reaches the frame's fields, so late repeats in a long tick
        ; drew queued horizon blits over the 3D. Count from this picture instead
        ; and add the tick's fields back afterwards.
        movea.l (c2_h0,pc),a2
        adda.l #$125e,a2
        move.w (a2),-(sp)
        clr.w (a2)
        bsr c2_scene_call
        movea.l (c2_h0,pc),a2
        adda.l #$125e,a2
        move.w (sp)+,d0
        add.w d0,(a2)
        bsr d3_restore
        bsr c2_repeat_boxes
        lea (c2_stage_saved,pc),a2
        bsr c2_load_stage
        lea (c2_repeat_pictures,pc),a0
        addq.l #1,(a0)
        bsr c2_publish
        rts

; A2 is a packed 23-byte snapshot. Tables contain only A3's persistent renderer
; effects plus the camera's one-use mirror request. Scratch stays native.
c2_save_stage
        lea (c2_stage_ranges,pc),a3
.range
        move.l (a3)+,d0
        beq.s .done
        movea.l (c2_h0,pc),a1
        adda.l d0,a1
        move.w (a3)+,d0
.byte
        move.b (a1)+,(a2)+
        dbf d0,.byte
        bra.s .range
.done
        rts
c2_load_stage
        lea (c2_stage_ranges,pc),a3
.range
        move.l (a3)+,d0
        beq.s .done
        movea.l (c2_h0,pc),a1
        adda.l d0,a1
        move.w (a3)+,d0
.byte
        move.b (a2)+,(a1)+
        dbf d0,.byte
        bra.s .range
.done
        rts
c2_stage_ranges
        dc.l $257c4
        dc.w 4
        dc.l $3a746
        dc.w 7
        dc.l $3a770
        dc.w 3
        dc.l $3a820
        dc.w 3
        dc.l $3a828
        dc.w 1
        dc.l 0
c2_stage_entry ds.b 23
c2_stage_saved ds.b 23
        CNOP 0,4
c2_repeat_pictures dc.l 0
c2_replay_pictures dc.l 0
c2_scene_ready dc.w 0

        CNOP 0,4
c4_deferred dc.l 0              ; key changes held back by the interrupt
c4_applied dc.l 0               ; held-back changes shown at a scan
c4_live dc.w 0
c4_keys ds.b 128                ; C4_* state per raw key

        CNOP 0,4
c2_h0 dc.l 0
c2_h1 dc.l 0
c2_h2 dc.l 0
c2_pacer_rest dc.l 0
c2_submit dc.l 0
c2_serial dc.l 0
c2_sound_serial dc.l 0
c2_pictures dc.l 0
c2_clock ds.b WC_SIZE
c2_mode dc.w 0
c2_draw_mode dc.w 0
c2_in_tick dc.w 0
c2_native_rate dc.w 0
c2_beam_max dc.w 0
d2_start dc.l 0                 ; field the current picture started
d2_pictures dc.l 0
d2_latest dc.l 0                ; pictures longer than a tick: alpha 0
d2_kind dc.w 0
d2_pending dc.w 0               ; started, first displayed field not yet seen
d2_phase dc.w 0                 ; fields since the current tick fell due
d2_interval dc.w 0              ; fields of the next tick
d2_lead dc.w 0                  ; lead used for this picture
d2_period dc.w 0                ; fields since the previous picture started
d2_alpha dc.w 0                 ; unsigned Q14, at most $8000
d2_leads dc.w 0,0               ; last measured lead per kind
d2_weight dc.w 0                ; the history's, unsigned Q14 (D10)
d10_pits ds.b 3*D10_PIT          ; per pit sprite (D10)
d1_current dc.w 0
d1_buffers ds.b 2*D1_SIZE
d3_pictures dc.l 0              ; pictures seen
d3_staged_pictures dc.l 0
d3_latest dc.l 0                ; alpha 0: no history used
d3_snapped dc.l 0               ; history not the previous tick of this epoch and view
d3_debris dc.l 0                ; not staged: drawing may set the debris deadline
d3_records dc.l 0               ; records held because their pose flag changed
d3_written dc.l 0               ; VERIFY: the renderer wrote a staged byte
d3_checked dc.l 0               ; VERIFY: restores checked against a snapshot
d3_faults dc.l 0                ; VERIFY: restore differs from its snapshot
d3_check_tick dc.l 0            ; VERIFY: in-tick restore, checked at that tick's snapshot
d4_predicted dc.l 0             ; pictures with a predicted camera
d4_jumps dc.l 0                 ; camera jumped: snapped
d4_anchors dc.l 0               ; road anchor moved by the prediction
d4_held dc.l 0                  ; anchor search left the main track: tick's anchor kept
d4_faults dc.l 0                ; VERIFY: derived values differ from the game's
d4_position dc.l 0,0            ; predicted world X/Z for the segment search
d4_spring dc.w 0                ; spring word at the stage, for the horizon
d5_predicted dc.l 0             ; car records predicted
d5_held dc.l 0                  ; car records kept at the tick
d5_moved dc.l 0                 ; predicted records on another segment
d5_track dc.l 0                 ; cars drawn track-driven after a pose flag change
d5_applied dc.l 0               ; those flipped in the game's records for the draw
d7_aimed dc.l 0                 ; external cameras placed from the predicted car
d7_faults dc.l 0                ; VERIFY: the tick's camera placed differs from the game's
d7_record ds.b $80              ; a staged car as the pose accessor reads it
d3_active dc.w 0
d3_kind dc.w 0
d3_source dc.w 0                ; 0 authoritative, 1 previous tick, 2 predicted
d3_saved ds.b D3_SIZE
d3_staged ds.b D3_SIZE
        ENDC

; BASELINE_PATCHES_BEGIN: mandatory B3 loader patches, never feature-gated.
patch_582992
        PL_START
        PL_L $982,$22116000
        PL_L $345c4,$4e714e71
        PL_PS $6f840,keyboard
        PL_B $a79ce,$ff
        PL_L $a7a42,'save'
        PL_W $a7a46,$7300
        ; BASELINE_PATCHES_END
        IFNE DEVELOPER
        PL_IFC3X 0
        ; PERF_RANGE h0:1288 4 custom=3 bit=0 variant=582992
        PL_NOP $1288,4
        PL_ENDIF
        PL_IFC3X 1
        ; Polygon edge walk and four-plane span fill; measurement only.
        ; PERF_RANGE h0:1f388 2 custom=3 bit=1 variant=582992
        PL_R $1f388
        PL_ENDIF
        ENDC
        IFNE VERIFY
        PL_IFC5X 0
        ; PERF_RANGE h0:3c9d2 6 custom=5 bit=0 variant=582992
        PL_PS $3c9d2,verify_pacer
        PL_ENDIF
        ENDC
        PL_END
        IFNE DEVELOPER
; The C2-C4 clock hooks, applied after the main list unless the CPU is a 68000
; (user decision: the 68000 keeps the native frame-locked pacer by default).
patch_582992_clock
        PL_START
        PL_IFC2X 8
        ; The edge tracer's X-major steps, one division per edge instead of a loop per pixel.
        ; PERF_RANGE h0:1ef74 6 custom=2 bit=8 variant=582992
        PL_PS $1ef74,e4_trace_right
        ; PERF_RANGE h0:1efde 6 custom=2 bit=8 variant=582992
        PL_PS $1efde,e4_trace_left
        ; The sky band's strip: a fast copy after each build, read by E3's CPU blits.
        ; PERF_RANGE h0:20e 6 custom=2 bit=8 variant=582992
        PL_PS $20e,e4_strip_build
        ; PERF_RANGE h2:1f41e 6 custom=2 bit=8 variant=582992
        PL_PS $8e7b2,e4_sky_source
        PL_ENDIF
        PL_IFC2X 1
        ; PERF_RANGE h0:3c8d2 6 custom=2 bit=1 variant=582992
        PL_PS $3c8d2,c2_live_entry
        ; PERF_RANGE h0:3c94a 6 custom=2 bit=1 variant=582992
        PL_PS $3c94a,c4_scan
        ; PERF_RANGE h0:3cc8e 6 custom=2 bit=1 variant=582992
        PL_PS $3cc8e,c4_scan
        ; PERF_RANGE h0:3c962 6 custom=2 bit=1 variant=582992
        PL_PS $3c962,c3_live_pause
        ; PERF_RANGE h0:3ccba 6 custom=2 bit=1 variant=582992
        PL_PS $3ccba,c3_replay_pause
        ; PERF_RANGE h0:3b6de 6 custom=2 bit=1 variant=582992
        PL_PS $3b6de,c3_pause_begin
        ; PERF_RANGE h0:3b8b4 6 custom=2 bit=1 variant=582992
        PL_PS $3b8b4,c3_pause_begin
        ; PERF_RANGE h0:3ba24 6 custom=2 bit=1 variant=582992
        PL_PS $3ba24,c3_reconstruct
        ; PERF_RANGE h0:3cbd6 6 custom=2 bit=1 variant=582992
        PL_PS $3cbd6,c3_replay_enter
        ; PERF_RANGE h0:3ca26 6 custom=2 bit=1 variant=582992
        PL_PS $3ca26,c3_race_exit
        ; PERF_RANGE h0:2cc3c 6 custom=2 bit=1 variant=582992
        PL_PS $2cc3c,c2_vbl
        ; PERF_RANGE h0:3c8f6 6 custom=2 bit=1 variant=582992
        PL_PS $3c8f6,c2_live_head
        ; PERF_RANGE h0:3cc40 6 custom=2 bit=1 variant=582992
        PL_PS $3cc40,c2_replay_head
        ; Entry replaces first six bytes of a ten-byte MOVE; tail resumes at +$127C.
        ; PERF_RANGE h0:1272 6 custom=2 bit=1 variant=582992
        PL_P $1272,c2_pacer
        ; PERF_RANGE h0:3c9ba 6 custom=2 bit=1 variant=582992
        PL_PS $3c9ba,c2_scene
        ; PERF_RANGE h0:3cce8 6 custom=2 bit=1 variant=582992
        PL_PS $3cce8,c2_scene
        ; PERF_RANGE h2:1dd24 6 custom=2 bit=1 variant=582992
        PL_P $8d0b8,c2_hud_icon
        ; PERF_RANGE h2:1dc84 6 custom=2 bit=1 variant=582992
        PL_P $8d018,c2_hud_background_clear
        ; PERF_RANGE h2:1dcbc 6 custom=2 bit=1 variant=582992
        PL_P $8d050,c2_hud_background_copy
        ; PERF_RANGE h2:1de58 6 custom=2 bit=1 variant=582992
        PL_P $8d1ec,c2_hud_box
        ; PERF_RANGE h2:1df24 6 custom=2 bit=1 variant=582992
        PL_P $8d2b8,c2_hud_copy
        ; PERF_RANGE h2:1df92 6 custom=2 bit=1 variant=582992
        PL_P $8d326,c2_hud_top
        ; PERF_RANGE h2:1ea40 6 custom=2 bit=1 variant=582992
        PL_P $8ddd4,c2_hud_digit
        ; PERF_RANGE h2:1eb9e 6 custom=2 bit=1 variant=582992
        PL_P $8df32,c2_hud_image
        ; PERF_RANGE h2:1f128 6 custom=2 bit=1 variant=582992
        PL_P $8e4bc,c2_hud_glyph
        ; PERF_RANGE h2:1f928 6 custom=2 bit=1 variant=582992
        PL_P $8ecbc,c2_hud_gear
        ; PERF_RANGE h2:1f974 6 custom=2 bit=1 variant=582992
        PL_P $8ed08,c2_hud_rpm
        ; PERF_RANGE h2:1fa6e 6 custom=2 bit=1 variant=582992
        PL_P $8ee02,c2_hud_assist
        ; PERF_RANGE h2:1f9b8 6 custom=2 bit=1 variant=582992
        PL_P $8ed4c,c2_hud_rpm_pixels
        ; PERF_RANGE h2:1f9e0 6 custom=2 bit=1 variant=582992
        PL_P $8ed74,c2_hud_rpm_end
        ; Replay R painting belongs to publication, not the world tick.
        ; PERF_RANGE h0:3ccfa 6 custom=2 bit=1 variant=582992
        PL_PS $3ccfa,c2_replay_tick_paint
        ; PERF_RANGE h0:1f392 6 custom=2 bit=1 variant=582992
        PL_P $1f392,c2_fill
        ; PERF_RANGE h0:147c 6 custom=2 bit=1 variant=582992
        PL_P $147c,c2_sprite
        ; PERF_RANGE h2:1e14e 6 custom=2 bit=1 variant=582992
        PL_P $8d4e2,c2_clear
        ; PERF_RANGE h2:1f3ba 6 custom=2 bit=1 variant=582992
        PL_P $8e74e,c2_sky
        ; PERF_RANGE h2:1f562 6 custom=2 bit=1 variant=582992
        PL_P $8e8f6,c2_sides
        ; PERF_RANGE h2:1f77c 6 custom=2 bit=1 variant=582992
        PL_P $8eb10,c2_lights
        ; PERF_RANGE h2:1f850 6 custom=2 bit=1 variant=582992
        PL_P $8ebe4,c2_hands
        ; PERF_RANGE h2:1e6cc 6 custom=2 bit=1 variant=582992
        PL_P $8da60,c2_blit_queue
        ; Pending-exchange wait and blitter-fill selection; resumes at h2+$27D78.
        ; PERF_RANGE h2:27d62 6 custom=2 bit=1 variant=582992
        PL_PS $970f6,e3_scene_wait
        ; PERF_RANGE h2:1dd1a 6 custom=2 bit=1 variant=582992
        PL_PS $8d0ae,c2_pair_a0_a2
        ; PERF_RANGE h2:1e046 6 custom=2 bit=1 variant=582992
        PL_PS $8d3da,c2_pair_a0_a2
        ; PERF_RANGE h2:1f91e 6 custom=2 bit=1 variant=582992
        PL_PS $8ecb2,c2_pair_a0_a2
        ; PERF_RANGE h2:1f9a6 6 custom=2 bit=1 variant=582992
        PL_PS $8ed3a,c2_pair_a0_a2
        ; PERF_RANGE h2:1fa58 6 custom=2 bit=1 variant=582992
        PL_PS $8edec,c2_pair_a0_a2
        ; PERF_RANGE h2:1de4e 6 custom=2 bit=1 variant=582992
        PL_PS $8d1e2,c2_pair_a5_a6
        ; PERF_RANGE h2:1ea36 6 custom=2 bit=1 variant=582992
        PL_PS $8ddca,c2_pair_a5_a6
        ; PERF_RANGE h2:1eb94 6 custom=2 bit=1 variant=582992
        PL_PS $8df28,c2_pair_a5_a6
        ; PERF_RANGE h2:1f10e 6 custom=2 bit=1 variant=582992
        PL_PS $8e4a2,c2_pair_a1_a2
        ; PERF_RANGE h2:2a2c8 6 custom=2 bit=1 variant=582992
        PL_PS $9965c,d10_pit_a
        ; PERF_RANGE h2:2a33a 6 custom=2 bit=1 variant=582992
        PL_PS $996ce,d10_pit_b
        ; PERF_RANGE h2:2a38a 6 custom=2 bit=1 variant=582992
        PL_PS $9971e,d10_pit_c
        PL_ENDIF
        PL_END
        ENDC
; BASELINE_PATCHES_BEGIN: mandatory B3 loader patches.
patch_582988
        PL_START
        PL_L $982,$22116000
        PL_L $345d8,$4e714e71
        PL_PS $6f856,keyboard
        PL_B $a79c6,$ff
        PL_L $a7a3a,'save'
        PL_W $a7a3e,$7300
        PL_END
patch_582780
        PL_START
        PL_L $978,$22116000
        PL_L $345ce,$4e714e71
        PL_PS $6f84a,keyboard
        PL_B $a791e,$ff
        PL_L $a7992,'save'
        PL_W $a7996,$7300
        PL_END
; BASELINE_PATCHES_END
names_rnc
        INCBIN tmp/slave/names.rnc
        EVEN

        IFNE DEVELOPER
        CNOP 0,4
c2_hud_buffer ds.b C2_HUD_STRIDE*C2_HUD_CAPACITY
        ENDC
