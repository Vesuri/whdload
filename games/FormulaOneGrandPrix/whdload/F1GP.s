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
        IFNE VERIFY
slv_Version = 18             ; resload_Log is VERIFY-only
        ELSE
slv_Version = 17
        ENDC
slv_Flags = WHDLF_NoError|WHDLF_EmulPriv|WHDLF_ClearMem|WHDLF_Examine
slv_keyexit = $59
CHIPMEMSIZE = $80000
FASTMEMSIZE = $80000
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
slv_config
        dc.b 'C1:B:Skip intro;'
        dc.b 'C2:X:Enable CPU caches:0;'
        IFNE VERIFY
        dc.b 'C5:X:Verify pacer relay:0;'
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
        ; The old loader's CPU mask leaves both caches disabled.
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
        move.l d7,a1
        move.l (_resload,pc),a2
        jsr (resload_PatchSeg,a2)
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
        jsr (-324,a6)        ; SetPrefs, same D1 as original
        lea (110,sp),sp
        movem.l (sp)+,d0-a6
        rts
keyboard
        ror.b #1,d0
        eor.b #$ff,d0
        cmp.b (_keyexit,pc),d0
        beq quit
        rts
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
        IFNE VERIFY
        PL_IFC5X 0
        ; PERF_RANGE h0:3c9d2 6 custom=5 bit=0 variant=582992
        PL_PS $3c9d2,verify_pacer
        PL_ENDIF
        ENDC
        PL_END
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
