 IFND COVERAGE_MOUSE_TEST
COVERAGE_MOUSE_TEST = 0
 ENDC
 IFNE COVERAGE_MOUSE_TEST
 IFND COVERAGE_INPUT
 FAIL "COVERAGE_MOUSE_TEST requires coverage input"
 ENDC
 ENDC
; Powerdrome release slave. Original install by Galahad/Fairlight.
; WHDLoad 20 KickEmu supplies the OS; interface 17 requires no v20-only feature.
 INCLUDE whdload.i
 INCLUDE whdmacros.i
 INCLUDE lvo/dos.i
 INCLUDE exec/memory.i
 INCLUDE exec/execbase.i
 IFND VERIFY_PHASE
VERIFY_PHASE = 0
 ENDC
 IFNE VERIFY_PHASE
 IFND VERIFY
 FAIL "VERIFY_PHASE requires VERIFY"
 ENDC
 ENDC
 IFND COVERAGE_AUDIO_KEYS
COVERAGE_AUDIO_KEYS = 0
 ENDC
 IFNE COVERAGE_AUDIO_KEYS
 IFNE COVERAGE_AUDIO_KEYS-1
 FAIL "COVERAGE_AUDIO_KEYS must be 0 or 1"
 ENDC
 IFND VERIFY
 FAIL "COVERAGE_AUDIO_KEYS requires VERIFY"
 ENDC
 IFND COVERAGE_INPUT
 FAIL "COVERAGE_AUDIO_KEYS requires COVERAGE_INPUT"
 ENDC
 ENDC
 IFND VERIFY_CHIPMEMSIZE
CHIPMEMSIZE = $80000
 ELSE
 IFND VERIFY
 FAIL "VERIFY_CHIPMEMSIZE requires VERIFY"
 ENDC
 IFNE VERIFY_CHIPMEMSIZE-$80000
 IFNE VERIFY_CHIPMEMSIZE-$100000
 FAIL "VERIFY_CHIPMEMSIZE must be $80000 or $100000"
 ENDC
 ENDC
CHIPMEMSIZE = VERIFY_CHIPMEMSIZE
 ENDC
 IFNE VERIFY_PHASE
FASTMEMSIZE = $60000 ; private 256 KiB phase ring in addition to normal arena
 ELSE
FASTMEMSIZE = $20000
 ENDC
NUMDRIVES = 1
WPDRIVES = 0
DISKSONBOOT
SETPATCH
CBDOSLOADSEG
slv_Version = 17
slv_Flags = WHDLF_NoError
slv_keyexit = $59
 INCLUDE whdload/kick13.s
slv_name dc.b "Powerdrome",0
slv_copy dc.b "1989 Electronic Arts",0
slv_info dc.b "Installed by Galahad/Fairlight",10,"Enhancements by Vesuri",10,"Version 2.0 (13.10.2026)",0
slv_CurrentDir dc.b 0
slv_config
 dc.b "C1:B:Enhanced framerate;"
 IFD VERIFY
 dc.b "C2:L:Rendering experiment:Bitmap and code,Bitmap only,Bitmap code and scratch,Bitmap and scratch;"
 dc.b "C4:B:Twin planar drawing for verification;"
 IFD COVERAGE_INPUT
 dc.b "C5:L:Verification route:Off,Title demo,Practice,Coverage practice,Coverage race,Coverage cruise,Coverage second course,Timing controls,Timing pause,Timing joystick,Timing engine heat,Timing forces,Timing sessions,Timing rescue;"
 ELSE
 dc.b "C5:L:Verification route:Off,Title demo,Practice;"
 ENDC
 ENDC
 dc.b 0
 EVEN

_cb_dosLoadSeg
 lsl.l #2,d0
 move.l d0,a0
 lea endcliname(pc),a1
 moveq #0,d2
 move.b (a0),d2
.cmp cmpm.b (a0)+,(a1)+
 dbne d2,.cmp
 bne.s .done
 lea pl_endcli(pc),a0
 move.l d1,a1
 move.l _resload(pc),a2
 jsr resload_PatchSeg(a2)
.done rts
endcliname dc.b 6,"endcli"
 EVEN
pl_endcli PL_START
 PL_P $4,launch_pd
 PL_END

launch_pd
 IFNE VERIFY_PHASE
 bsr phase_allocate
 ENDC
 bsr reserve_arena
 move.l (4).w,a6
 moveq #0,d0
 lea dosname(pc),a1
 jsr -552(a6)
 move.l d0,a6
 lea gamename(pc),a0
 move.l a0,d1
 jsr _LVOLoadSeg(a6)
 tst.l d0
 beq.s .error
 lsl.l #2,d0
 move.l d0,a3
 lea 4(a3),a1
 ; Require the exact original Copylock signature before installing its replacement.
 move.l a1,a0
 adda.l #$843c,a0
 cmp.l #$2f0e4dfa,(a0)
 bne.s .error
 lea pl_game(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 lea tags(pc),a0
 jsr resload_Control(a2)
 bsr select_features
 lea 4(a3),a1
 bsr install_planar
 bsr install_timing
 IFD VERIFY
 move.l custom5(pc),d0
 beq.s .run
 lea pl_verify(pc),a0
 lea 4(a3),a1
 jsr resload_Patch(a2)
 move.l custom5(pc),d0
 cmp.l #2,d0
 IFD COVERAGE_INPUT
 blo.s .run
 ELSE
 bne.s .run
 ENDC
 lea pl_practice(pc),a0
 lea 4(a3),a1
 jsr resload_Patch(a2)
 IFD COVERAGE_INPUT
 bsr install_coverage_patches
 ENDC
.run
 IFNE VERIFY_PHASE
 ; Chain the final installed coverage entry as well as the planar/timing hooks.
 bsr install_phase
 ENDC
 ENDC
 ; resload calls may poison scratch registers, especially with MMU checks.
 ; DOS program entry requires a valid argument pointer and length.
 lea launch_args(pc),a0
 moveq #0,d0
 jmp (a3)
.error
 pea TDREASON_WRONGVER
 move.l _resload(pc),a2
 jmp resload_Abort(a2)
 ; Resolve the single opt-in once. Internal custom1/custom3 enable the two
 ; installers together; custom3 is not a WHDLoad option. Cache policy is untouched.
select_features
 movem.l d0-d1/a0,-(sp)
 lea custom1(pc),a0
 move.l (a0),d0
 clr.l (a0)
 clr.l custom3-custom1(a0)
 tst.l d0
 beq.s .done
 move.l cpu_attn(pc),d1
 btst #AFB_68020,d1
 beq.s .done
 ; Both enhancements require real fast RAM. Otherwise keep both native paths.
 move.l perf_bitmap(pc),d1
 beq.s .done
 moveq #1,d0
 move.l d0,(a0)
 move.l d0,custom3-custom1(a0)
.done
 movem.l (sp)+,d0-d1/a0
 rts

pl_game PL_START
 PL_P $843c,copylock
 PL_END
; The original also returned a legacy registration value in D2. The caller
; replaces its low word at game $173b2 before use, then MOVEQ at $16c4c replaces
; the whole register. Matched loader captures confirm convergence; no tag needed.
copylock move.l #$766cc95c,d0
 rts
launch_args dc.b 10,0
dosname dc.b "dos.library",0
gamename dc.b "Powerdrome:PD",0
 EVEN
 ; Configuration emits no bytes here; coverage needs WORLD20 before its key hook.
TIMING_FLAGS_ONLY SET 1
 INCLUDE timing.s
TIMING_FLAGS_ONLY SET 0

 IFD VERIFY
 INCLUDE verify_input.s
 IFD COVERAGE_INPUT
 INCLUDE coverage.s
 ENDC
 ENDC
tags dc.l WHDLTAG_ATTNFLAGS_GET
cpu_attn dc.l 0
 dc.l WHDLTAG_CUSTOM1_GET
custom1 dc.l 0
 IFD VERIFY
 dc.l WHDLTAG_CUSTOM2_GET
custom2 dc.l 0
 dc.l WHDLTAG_CUSTOM4_GET
custom4 dc.l 0
 dc.l WHDLTAG_CUSTOM5_GET
custom5 dc.l 0
 ENDC
 dc.l TAG_DONE
custom3 dc.l 0 ; resolved internal timing enable, not a user option
 IFND VERIFY
custom2 dc.l 0
 ENDC
 INCLUDE timing.s
 INCLUDE planar.s
 INCLUDE fast_raster.s


 IFNE VERIFY_PHASE
 INCLUDE phase.s
 ENDC

 IFNE TIMING_MOUSE
timing_mouse_sine
 INCLUDE ../tmp/build/mouse-sine.i
 ENDC
