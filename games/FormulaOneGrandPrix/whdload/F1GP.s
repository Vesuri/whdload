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
        IFNE DEVELOPER
        dc.b 'C2:X:Developer - VBL world clock:1;'
        dc.b 'C2:X:Developer - VBL world clock on a 68000 too:2;'
        dc.b 'C2:X:Developer - presentation snapshots and timing:3;'
        dc.b 'C3:X:Ceiling - no pacer wait:0;'
        dc.b 'C3:X:Ceiling - no polygon fill:1;'
        dc.b 'C4:X:Ceiling - no preference notifications:0;'
        dc.b 'C4:X:C2 diagnostic - 20 field delay per batch:1;'
        dc.b 'C4:X:C2 diagnostic - retain native painting:2;'
        ENDC
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
        IFNE DEVELOPER
        dc.l WHDLTAG_CUSTOM4_GET
preference_options dc.l 0
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
D1_SIZE = D1_HEADER+156+27*D1_RECORD
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
d1_done
        rts
; Hunk*4, offset, words-1: view state, chase/player, published camera,
; yaw coefficients, TV/chase parameters, horizon and viewport.
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
; a tick (that lead, or the period since the last picture started, exceeds the next
; interval) the picture shows the latest state: alpha 0. Read-only for the game.
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
        movea.l (c2_h0,pc),a2
        adda.l #$124e,a2
        move.l 8(a2),(a2)      ; bitmap base, never the external-view viewport
        bsr c2_submit_call
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
        bsr c2_scene_call
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
d1_current dc.w 0
d1_buffers ds.b 2*D1_SIZE
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
