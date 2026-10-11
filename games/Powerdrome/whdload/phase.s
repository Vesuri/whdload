; VERIFY-only PAL phase clock. 16384 sixteen-byte records in separately allocated
; memory; no instrumentation or allocation in normal/ordinary coverage builds.
; Header: signature, buffer, sequence, capacity, sample PC. Record: sequence,
; game VBL count, VPOSR/VHPOSR pair, event ID, completed world ticks (low word).
phase_allocate
 movem.l d0-d1/a0-a2/a6,-(sp)
 move.l (4).w,a6
 move.l #16384*16,d0
 move.l #MEMF_FAST|MEMF_CLEAR,d1
 jsr _LVOAllocMem(a6)
 lea phase_state(pc),a0
 move.l d0,8(a0)
 beq.s .failed
 lea phase_sample(pc),a1
 move.l a1,20(a0)
 movem.l (sp)+,d0-d1/a0-a2/a6
 rts
.failed
 pea phase_nomem(pc)
 pea TDREASON_FAILMSG
 move.l _resload(pc),a2
 jmp resload_Abort(a2)

phase_nomem dc.b "Phase ring allocation failed",0
 EVEN

install_phase
 movem.l d0-d2/a0-a2,-(sp)
 move.l (4).w,a0
 btst #AFB_68010,AttnFlags+1(a0)
 beq.s .cpu_ready
 lea phase_record(pc),a0
 move.w #$42e7,(a0)
.cpu_ready
 IFNE TIMING_PERIODIC
 IFNE TIMING_WORLD
 ; Full timing closes scheduler scopes itself, including incident presentations.
 move.l custom3(pc),d0
 beq.s .world_ready
 lea phase_native_world_end(pc),a0
 move.l #$4e714e71,(a0)
 move.w #$4e71,4(a0)
.world_ready
 ENDC
 ENDC
 move.l perf_game(pc),a1
 ; Copy relocated absolute entry instructions, including the renderer's C1 JMP.
 lea phase_render_native(pc),a0
 move.l a1,a2
 adda.l #$10df2,a2
 move.l (a2),(a0)
 move.l a1,a2
 adda.l #$10df6,a2
 move.w (a2),4(a0)
 move.l a1,d0
 add.l #$10df8,d0
 move.l d0,8(a0)
 lea phase_world_native(pc),a0
 move.l a1,a2
 adda.l #$ca3e,a2
 move.l (a2),(a0)
 move.l a1,a2
 adda.l #$ca42,a2
 move.w (a2),4(a0)
 move.l a1,d0
 add.l #$ca44,d0
 move.l d0,8(a0)
 lea phase_present_native(pc),a0
 move.l a1,d0
 add.l #$7f7a,d0
 move.l d0,2(a0)
 move.l a1,a2
 adda.l #$805a,a2
 move.l (a2),6(a0)
 move.l a1,a2
 adda.l #$805e,a2
 move.w (a2),10(a0)
 move.l a1,d0
 add.l #$8060,d0
 move.l d0,14(a0)
 lea phase_hud_native(pc),a0
 move.l a1,d0
 add.l #$1181c,d0
 move.l d0,2(a0)
 move.l a1,d0
 add.l #$d8ee,d0
 move.l d0,8(a0)
 ; The HUD entry replaces ten bytes, so replay its second absolute call too.
 move.l a1,a2
 adda.l #$d8ee,a2
 move.l (a2),12(a0)
 move.l a1,a2
 adda.l #$d8f2,a2
 move.w (a2),16(a0)
 move.l a1,d0
 add.l #$d8f4,d0
 move.l d0,20(a0)
 ; Redirect HUD trampoline's jump to the copied second instruction.
 lea 12(a0),a2
 move.l a2,8(a0)
 lea phase_timer_zero(pc),a0
 move.l a1,d0
 add.l #$f0e2,d0
 move.l d0,2(a0)
 lea phase_timer_nonzero(pc),a0
 addq.l #8,d0
 move.l d0,2(a0)
 lea pl_phase(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 movem.l (sp)+,d0-d2/a0-a2
 rts
pl_phase PL_START
 PL_P $ca3e,phase_world
 PL_P $10df2,phase_render
 PL_PS $112a6,phase_wait
 PL_P $d8ea,phase_hud
 PL_P $f0dc,phase_timer
 PL_P $8056,phase_present
 PL_END

phase_world
 bsr phase_record
 dc.w 1
 bra.w phase_world_native
phase_world_native
 dcb.w 3,0
 jmp $0.l
phase_render
phase_native_world_end
 ; Replaced with NOPs when the full scheduler owns the world boundaries.
 bsr phase_record
 dc.w 2
 bsr phase_record
 dc.w 3
 bsr phase_render_native
phase_render_return
 bsr phase_record
 dc.w 4
 rts
phase_render_native
 dcb.w 3,0
 jmp $0.l
phase_wait
 bsr phase_record
 dc.w 5
.wait
 tst.w $494(a6)
 beq.s .wait
 bsr phase_record
 dc.w 6
 rts
phase_hud
 bsr phase_record
 dc.w 9
 bsr phase_hud_native
 bsr phase_record
 dc.w 10
 rts
phase_hud_native
 jsr $0.l
 jmp $0.l
 jsr $0.l
 jmp $0.l
phase_timer
 bsr phase_record
 dc.w 11
 bsr .native
 bsr phase_record
 dc.w 12
 rts
.native
 tst.w $da(a6)
 bne.s phase_timer_nonzero
phase_timer_zero jmp $0.l
phase_timer_nonzero jmp $0.l
phase_present
 bsr phase_record
 dc.w 13
 bsr phase_present_native
 bsr phase_record
 dc.w 14
 rts
phase_present_native
 jsr $0.l
 movea.l #0,a1
 jmp $0.l

; Inline word after BSR is the event ID. Preserve CCR and every scratch register.
; Retry vertical boundary crossings or a VBL update between the two beam reads.
phase_record
 move.w sr,-(sp)
 movem.l d0-d3/a0-a2,-(sp)
 move.l 30(sp),a2
 moveq #0,d2
 move.w (a2)+,d2
 move.l a2,30(sp)
 lea phase_state(pc),a0
 move.l perf_game(pc),a1
phase_retry
 move.l $48fe(a1),d0
phase_sample
 move.l $dff004,d1
 move.l $dff004,d3
 eor.l d1,d3
 and.l #$1ff00,d3
 bne.s phase_retry
 cmp.l $48fe(a1),d0
 bne.s phase_retry
 cmp.w #15,d2
 bne.s .not_tick
 addq.w #1,24(a0)
.not_tick
 move.l 12(a0),d3
 move.l d3,a1
 and.l #16383,d3
 lsl.l #4,d3
 add.l 8(a0),d3
 exg d3,a1
 move.l d3,(a1)+
 move.l d0,(a1)+
 move.l d1,(a1)+
 move.w d2,(a1)+
 move.w 24(a0),(a1)
 addq.l #1,12(a0)
 movem.l (sp)+,d0-d3/a0-a2
 move.w (sp)+,ccr
 rts
phase_state dc.b 'PDPHASE1'
 dc.l 0,0,16384,0
 dc.w 0
