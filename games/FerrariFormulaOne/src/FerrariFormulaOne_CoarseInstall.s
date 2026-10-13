; SPS 0481 coarse candidate installation, called after the public loader's
; official repairs. The host supplies selection/profile data, hunk bindings,
; FF1_HOST_CODE_SIZE, public_table/bound, and the step-1 RNG diagnostic entry.
; Selection 0 and fine selection 2 return without installing any coarse hooks.
; CPU-only code, ledger and snapshots use the existing public-memory owners.
 IFD FF1_COARSE_STEP
 IFD FF1_COARSE_NATIVE_EXACT
 IFND FF1_COARSE_020
 fail "FF1_COARSE_NATIVE_EXACT requires the 68020 coarse build"
 ENDC
 ENDC
start:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.l #$22f30,(a3)
 bne.w done
 move.l selection_path(pc),d0
 cmpi.l #1,d0
 bne.w done
 move.l a4,a2
 move.l $18(a3),d0
 lsl.l #2,d0
 suba.l d0,a2
 lea public_table(pc),a0
 move.l a2,(a0)
 move.l 160*4(a2),d0
 cmp.l public_bound(pc),d0
 beq.w done
 lea start(pc),a0
 lea public_bindings(pc),a1
 bsr.w FF1ApplyBindings
 tst.l d0
 bne.w C1Fault
 lea public_bound(pc),a0
 move.l 160*4(a2),(a0)
 bsr.w C1InstallUnload
 move.l $4.w,a6
 jsr -120(a6)
 lea C1Ledger(pc),a0
 move.l public_table(pc),a1
 bsr.w FF1PatchBegin
 tst.l d0
 bne.w C1Fault
 move.w #$4ef9,$65174
 lea C1Head(pc),a0
 move.l a0,$65176
 move.w #$4eb9,$6a304
 lea s2_rng_control(pc),a0
 move.l a0,$6a306
 ; All race exits funnel through the original cleanup call at $65f48.
 lea C1Exit(pc),a0
 move.w #$4ef9,$65f48
 move.l a0,$65f4a
 lea C1Ledger(pc),a0
 bsr.w FF1PatchSeal
 tst.l d0
 bne.w C1Fault
 bsr.w C1Flush
 move.l $4.w,a6
 jsr -126(a6)
done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
C1Flush:
 movem.l d0-d7/a0-a6,-(sp)
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 movem.l (sp)+,d0-d7/a0-a6
 rts
C1Activate:
 movem.l d0-d7/a0-a6,-(sp)
 move.w C1Control(pc),d0
 cmpi.w #2,d0
 bne.b .split
 lea C1NativeEnd(pc),a0
 move.w #$4ef9,$65f2e
 move.l a0,$65f30
 bsr.w C1Flush
 movem.l (sp)+,d0-d7/a0-a6
 rts
.split:
 ; Host ledger owns every changed native word until native race exit/unload.
 move.l $4.w,a6
 jsr -120(a6)
 lea C1Ledger(pc),a0
 move.l public_table(pc),a1
 bsr.w FF1PatchBegin
 tst.l d0
 bne.w C1Fault
 cmpi.w #$3039,$654ec
 bne.w C1Fault
 cmpi.w #$0006,$654ee
 bne.w C1Fault
 cmpi.w #$6f88,$654f0
 bne.w C1Fault
 cmpi.w #$3039,$65606
 bne.w C1Fault
 cmpi.w #$0001,$65608
 bne.w C1Fault
 cmpi.w #$c6a2,$6560a
 bne.w C1Fault
 cmpi.w #$4eb9,$65f2e
 bne.w C1Fault
 cmpi.w #$0002,$65f30
 bne.w C1Fault
 cmpi.w #$a130,$65f32
 bne.w C1Fault
 cmpi.w #$33c1,$24946
 bne.w C1Fault
 cmpi.w #$0002,$24948
 bne.w C1Fault
 cmpi.w #$4ad2,$2494a
 bne.w C1Fault
 cmpi.w #$4eb9,$65dca
 bne.w C1Fault
 cmpi.w #$0002,$65dcc
 bne.w C1Fault
 cmpi.w #$2c3a,$65dce
 bne.w C1Fault
 cmpi.w #$4eb9,$65dd8
 bne.w C1Fault
 cmpi.w #$0002,$65dda
 bne.w C1Fault
 cmpi.w #$2c3a,$65ddc
 bne.w C1Fault
 cmpi.w #$3039,$6c20c
 bne.w C1Fault
 cmpi.w #$0002,$6c20e
 bne.w C1Fault
 cmpi.w #$268e,$6c210
 bne.w C1Fault
 cmpi.w #$4279,$6c5de
 bne.w C1Fault
 cmpi.w #$0006,$6c5e0
 bne.w C1Fault
 cmpi.w #$a694,$6c5e2
 bne.w C1Fault
 cmpi.w #$48c0,$6c5f6
 bne.w C1Fault
 cmpi.w #$e380,$6c5f8
 bne.w C1Fault
 cmpi.w #$2040,$6c5fa
 bne.w C1Fault
 cmpi.w #$302e,$6c6ea
 bne.w C1Fault
 cmpi.w #$fff0,$6c6ec
 bne.w C1Fault
 cmpi.w #$48c0,$6c6ee
 bne.w C1Fault
 cmpi.w #$3039,$6c7c8
 bne.w C1Fault
 cmpi.w #$0006,$6c7ca
 bne.w C1Fault
 cmpi.w #$a694,$6c7cc
 bne.w C1Fault
 cmpi.w #$4eb9,$653fc
 bne.w C1Fault
 cmpi.w #$0002,$653fe
 bne.w C1Fault
 cmpi.w #$546a,$65400
 bne.w C1Fault
 cmpi.w #$3039,$654b8
 bne.w C1Fault
 cmpi.w #$0001,$654ba
 bne.w C1Fault
 cmpi.w #$c8b0,$654bc
 bne.w C1Fault
 IFD FF1_COARSE_NATIVE_EXACT
 ; Reuse audited native arithmetic only on the opt-in 68020 coarse path.
 ; The same race ledger owns and restores every changed instruction.
 move.w C2Enabled(pc),d0
 beq.b .native_exact_done
 bsr.w FF1InstallNativeExact
 move.l error(pc),d0
 bne.w C1Fault
.native_exact_done:
 ENDC
 IFD FF1_COARSE_NATIVE_000
 move.w C3Enabled(pc),d0
 beq.b .native_000_done
 bsr.w FF1InstallNative000
 move.l error(pc),d0
 bne.w C1Fault
.native_000_done:
 ENDC
 bsr.w FF1InstallPresentation
 move.l error(pc),d0
 bne.w C1Fault
 lea C1SkipSwap(pc),a0
 move.l a0,$654ee
 move.w #$4ef9,$654ec
 lea FF1SimulationTail(pc),a0
 move.l a0,$65608
 move.w #$4ef9,$65606
 lea C1End(pc),a0
 move.l a0,$65f30
 move.w #$4ef9,$65f2e
 lea C1Vbl(pc),a0
 move.l a0,$24948
 move.w #$4eb9,$24946
 lea FF1ClockTick(pc),a0
 move.l a0,$65dcc
 move.w #$4eb9,$65dca
 lea FF1ClockTick(pc),a0
 move.l a0,$65dda
 move.w #$4eb9,$65dd8
 lea C1RecoveryEntry(pc),a0
 move.l a0,$6c20e
 move.w #$4ef9,$6c20c
 lea C1RecoveryClear(pc),a0
 move.l a0,$6c5e0
 move.w #$4ef9,$6c5de
 lea C1RecoveryBody(pc),a0
 move.l a0,$6c5f8
 move.w #$4ef9,$6c5f6
 lea C1RecoveryDraw(pc),a0
 move.l a0,$6c6ec
 move.w #$4ef9,$6c6ea
 lea C1RecoveryExit(pc),a0
 move.l a0,$6c7ca
 move.w #$4ef9,$6c7c8
 lea C1Pause(pc),a0
 move.l a0,$653fe
 move.w #$4eb9,$653fc
 lea C1Resume(pc),a0
 move.l a0,$654ba
 move.w #$4eb9,$654b8
 lea C1Context(pc),a0
 moveq #100,d0
 bsr.w FF1TimeInit
 lea C1Active(pc),a0
 move.w #1,(a0)
 lea C1Ledger(pc),a0
 bsr.w FF1PatchSeal
 tst.l d0
 bne.w C1Fault
 bsr.w C1Flush
 move.l $4.w,a6
 jsr -126(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
C1SkipSwap:
 ; Preserve native per-step buffer views independently of physical publication.
 move.l $226ae,d0
 move.l $226b2,$226ae
 move.l d0,$226b2
 jmp $65542
C1InstallUnload:
 move.l C1UnloadInstalled(pc),d0
 bne.b .done
 move.l public_table(pc),a0
 move.l (a0),d0
 lsl.l #2,d0
 addi.l #4+$35c,d0
 move.l d0,a0
 cmpi.l #$48e7e00e,(a0)
 bne.w C1Fault
 cmpi.l #$202c0004,4(a0)
 bne.w C1Fault
 move.w #$4ef9,(a0)
 lea C1Unload(pc),a1
 move.l a1,2(a0)
 move.w #$4e71,6(a0)
 addq.l #8,d0
 lea C1UnloadJump+2(pc),a1
 move.l d0,(a1)
 lea C1UnloadInstalled(pc),a0
 move.l #1,(a0)
.done:
 rts
C1UnloadInstalled: dc.l 0
C1Ledger: ds.b 24
 IFD FF1_COARSE_NATIVE_000
C3Enabled: dc.w 1
 include "FerrariFormulaOne_Native000.s"
 ENDC
 IFD FF1_COARSE_NATIVE_EXACT
C2Enabled: dc.w 1
 include "FerrariFormulaOne_NativeExact.s"
 ENDC
 ENDC
