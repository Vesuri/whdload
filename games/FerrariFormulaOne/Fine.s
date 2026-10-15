; Production 68020+Fast entry; SPS 0481 bindings are generated at build time.
FF1_FINE_TEXT equ 1
FF1_FINE_BLIT_OWNER equ 1
start:
 move.l d0,-(sp)
 move.l selection_path(pc),d0
 cmpi.l #2,d0
 movem.l (sp)+,d0
 beq.b .fine
 rts
.fine:
 bsr.l public_bind
 cmpi.l #2,selection_path(pc)
 bne.b public_early_done
 bsr.l public_install_lifetime
 bsr.l public_begin_early
public_early_done:
 move.l d0,a1
 movem.l d0-a6,-(sp)
 move.w ccr,-(sp)
 cmpi.l #2,selection_path(pc)
 bne.w done
 cmp.l #$64a68,d0
 bne.w done
 lea (installed.l,pc),a0
 tst.l (a0)
 bne.w done
 cmpi.l #$48e73c00,$293d0
 bne.w bad
 cmpi.l #$4eb90002,$654e6
 bne.w bad
 cmpi.w #$a130,$654ea
 bne.w bad
 addq.l #1,(a0)
 lea (barrier.l,pc),a0
 move.l a0,$654e8
 bra.w done
bad:
 lea (error.l,pc),a0
 move.l #1,(a0)
 bra.w FF1ProductionFault
done:
 bsr.l public_seal
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
barrier:
 jsr $2a130
 movem.l d0-a6,-(sp)
 move.w ccr,-(sp)
 tst.w schedule_context+FF1T_STEP_MS(pc)
 bne.w finish
 bsr.l public_begin
 cmpi.l #2,selection_path(pc)
 bne.w finish
 bsr.l public_install_boundary
 cmpi.l #2,selection_path(pc)
 bne.w finish
 move.w modeval(pc),d0
 tst.w d0
 beq.b omit
 move.w #$4ef9,$293d0
 lea (FF1Divide020.l,pc),a1
plant:
 move.l a1,$293d2
omit:
 move.w #$4ef9,$65714
 lea (logic_tail.l,pc),a1
 move.l a1,$65716
 move.w #$4ef9,$65f2e
 lea (schedule_end.l,pc),a1
 move.l a1,$65f30
 bsr.w install_extras
keep_gauges:
 bsr.w install_velocity
 bsr.w install_position_bridge
 bsr.w install_fine_position
 bsr.w install_heading
 bsr.w install_steering
 bsr.w install_wear
 bsr.w install_events
 bsr.w install_clocks
 bsr.w install_counters
 bsr.w install_fuel
 bsr.w install_recovery
 bsr.l FF1InstallPresentation
 bsr.l B8InstallRenderCopies
 bsr.l FF1InstallOpponents
 ifgt FF1_NATIVE_EXACT
 bsr.l FF1InstallNativeExact
 endc
 bsr.l FF1RenderInstallColourElide
 bsr.l FF1RenderInstallBitmap
 bsr.l FF1RenderInstallFill
 bsr.l FF1RenderInstallClear
 bsr.l FF1RenderInstallGauges
 bsr.l FF1FinePauseInstall
 tst.l error(pc)
 bne.l FF1ProductionFault
 bsr.w schedule_install
 bsr.l FF1FineBlitAcquire
 ; Retain the accepted B8 CPU-cache policy. WHDLoad owns cache teardown.
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 move.l FF1_HOST_RESLOAD(a2),a2
 move.l #$13e,d0
 move.l #$13f,d1
 jsr $60(a2)
 bsr.l public_seal
finish:
 bsr.w schedule_begin
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
logic_tail:
 jmp FF1SimulationTail
 include "ProductionFault.s"
 include "FerrariFormulaOne_Math.s"
install_extras:
 cmpi.w #3,d0
 beq.b square
 cmpi.w #5,d0
 blo.b multiply
square:
 cmpi.l #$343c0200,$25770
 bne.w extra_bad
 lea (FF1SquareRoot020.l,pc),a1
 move.w #$4ef9,$25770
 move.l a1,$25772
multiply:
 cmpi.w #4,d0
 beq.b check_mul
 cmpi.w #5,d0
 blo.w extra_done
check_mul:
 cmpi.l #$4eb90002,$22910
 bne.w extra_bad
 cmpi.l #$9500d1ae,$22914
 bne.w extra_bad
 cmpi.l #$fff8600e,$22918
 bne.w extra_bad
 cmpi.l #$4eb90002,$24340
 bne.w extra_bad
 cmpi.l #$9500e680,$24344
 bne.w extra_bad
 cmpi.l #$2f002f11,$24348
 bne.w extra_bad
 cmpi.l #$4eb90002,$656ec
 bne.w extra_bad
 cmpi.l #$9500720a,$656f0
 bne.w extra_bad
 cmpi.l #$e2a0222f,$656f4
 bne.w extra_bad
 cmpi.l #$4eb90002,$65704
 bne.w extra_bad
 cmpi.l #$9500720a,$65708
 bne.w extra_bad
 cmpi.l #$e2a033c0,$6570c
 bne.w extra_bad
 cmpi.l #$4eb90002,$6586e
 bne.w extra_bad
 cmpi.l #$9500e080,$65872
 bne.w extra_bad
 cmpi.l #$33c00006,$65876
 bne.w extra_bad
 cmpi.l #$4eb90002,$65ab4
 bne.w extra_bad
 cmpi.l #$9500e080,$65ab8
 bne.w extra_bad
 cmpi.l #$33c00006,$65abc
 bne.w extra_bad
 cmpi.l #$4eb90002,$678d8
 bne.w extra_bad
 cmpi.l #$9500d1b9,$678dc
 bne.w extra_bad
 cmpi.l #$00032fb4,$678e0
 bne.w extra_bad
 cmpi.l #$4eb90002,$678fa
 bne.w extra_bad
 cmpi.l #$9500d1b9,$678fe
 bne.w extra_bad
 cmpi.l #$00032fb8,$67902
 bne.w extra_bad
 cmpi.l #$4eb90002,$67942
 bne.w extra_bad
 cmpi.l #$9500d1b9,$67946
 bne.w extra_bad
 cmpi.l #$00032fb4,$6794a
 bne.w extra_bad
 cmpi.l #$4eb90002,$67970
 bne.w extra_bad
 cmpi.l #$9500d1b9,$67974
 bne.w extra_bad
 cmpi.l #$00032fb8,$67978
 bne.w extra_bad
 cmpi.l #$4eb90002,$68896
 bne.w extra_bad
 cmpi.l #$95005a80,$6889a
 bne.w extra_bad
 cmpi.l #$222f0000,$6889e
 bne.w extra_bad
 cmpi.l #$4eb90002,$68944
 bne.w extra_bad
 cmpi.l #$9500e880,$68948
 bne.w extra_bad
 cmpi.l #$3080600e,$6894c
 bne.w extra_bad
 cmpi.l #$4eb90002,$6b0c2
 bne.w extra_bad
 cmpi.l #$9500e380,$6b0c6
 bne.w extra_bad
 cmpi.l #$2250d3c0,$6b0ca
 bne.w extra_bad
 cmpi.l #$4eb90002,$6cd5c
 bne.w extra_bad
 cmpi.l #$95007213,$6cd60
 bne.w extra_bad
 cmpi.l #$e2a03d40,$6cd64
 bne.w extra_bad
 cmpi.l #$4eb90002,$6cda8
 bne.w extra_bad
 cmpi.l #$95007213,$6cdac
 bne.w extra_bad
 cmpi.l #$e2a03d40,$6cdb0
 bne.w extra_bad
 cmpi.l #$4eb90002,$6d39e
 bne.w extra_bad
 cmpi.l #$9500720e,$6d3a2
 bne.w extra_bad
 cmpi.l #$e2a0322e,$6d3a6
 bne.w extra_bad
 cmpi.l #$4eb90002,$6d438
 bne.w extra_bad
 cmpi.l #$9500720e,$6d43c
 bne.w extra_bad
 cmpi.l #$e2a0322e,$6d440
 bne.w extra_bad
 cmpi.l #$4eb90002,$6db5e
 bne.w extra_bad
 cmpi.l #$95004480,$6db62
 bne.w extra_bad
 cmpi.l #$60183039,$6db66
 bne.w extra_bad
 cmpi.l #$4eb90002,$6dbfe
 bne.w extra_bad
 cmpi.l #$95004480,$6dc02
 bne.w extra_bad
 cmpi.l #$60183039,$6dc06
 bne.w extra_bad
 cmpi.l #$4eb90002,$6de24
 bne.w extra_bad
 cmpi.l #$9500e880,$6de28
 bne.w extra_bad
 cmpi.l #$222f000c,$6de2c
 bne.w extra_bad
 cmpi.l #$4eb90002,$6de74
 bne.w extra_bad
 cmpi.l #$95009190,$6de78
 bne.w extra_bad
 cmpi.l #$601e302e,$6de7c
 bne.w extra_bad
 cmpi.l #$4eb90002,$6defa
 bne.w extra_bad
 cmpi.l #$95009190,$6defe
 bne.w extra_bad
 cmpi.l #$526efffe,$6df02
 bne.w extra_bad
 cmpi.l #$4eb90002,$6dff8
 bne.w extra_bad
 cmpi.l #$9500e880,$6dffc
 bne.w extra_bad
 cmpi.l #$d0813239,$6e000
 bne.w extra_bad
 cmpi.l #$4eb90002,$6e9ce
 bne.w extra_bad
 cmpi.l #$95000680,$6e9d2
 bne.w extra_bad
 cmpi.l #$0000fde8,$6e9d6
 bne.w extra_bad
 cmpi.l #$4eb90002,$6e9de
 bne.w extra_bad
 cmpi.l #$95007212,$6e9e2
 bne.w extra_bad
 cmpi.l #$e2a04cdf,$6e9e6
 bne.w extra_bad
 cmpi.l #$4eb90002,$6ea30
 bne.w extra_bad
 cmpi.l #$95007212,$6ea34
 bne.w extra_bad
 cmpi.l #$e2a04e5e,$6ea38
 bne.w extra_bad
 move.l #$4c010800,$22910
 move.w #$4e71,$22914
 move.l #$4c010800,$24340
 move.w #$4e71,$24344
 move.l #$4c010800,$656ec
 move.w #$4e71,$656f0
 move.l #$4c010800,$65704
 move.w #$4e71,$65708
 move.l #$4c010800,$6586e
 move.w #$4e71,$65872
 move.l #$4c010800,$65ab4
 move.w #$4e71,$65ab8
 move.l #$4c010800,$678d8
 move.w #$4e71,$678dc
 move.l #$4c010800,$678fa
 move.w #$4e71,$678fe
 move.l #$4c010800,$67942
 move.w #$4e71,$67946
 move.l #$4c010800,$67970
 move.w #$4e71,$67974
 move.l #$4c010800,$68896
 move.w #$4e71,$6889a
 move.l #$4c010800,$68944
 move.w #$4e71,$68948
 move.l #$4c010800,$6b0c2
 move.w #$4e71,$6b0c6
 move.l #$4c010800,$6cd5c
 move.w #$4e71,$6cd60
 move.l #$4c010800,$6cda8
 move.w #$4e71,$6cdac
 move.l #$4c010800,$6d39e
 move.w #$4e71,$6d3a2
 move.l #$4c010800,$6d438
 move.w #$4e71,$6d43c
 move.l #$4c010800,$6db5e
 move.w #$4e71,$6db62
 move.l #$4c010800,$6dbfe
 move.w #$4e71,$6dc02
 move.l #$4c010800,$6de24
 move.w #$4e71,$6de28
 move.l #$4c010800,$6de74
 move.w #$4e71,$6de78
 move.l #$4c010800,$6defa
 move.w #$4e71,$6defe
 move.l #$4c010800,$6dff8
 move.w #$4e71,$6dffc
 move.l #$4c010800,$6e9ce
 move.w #$4e71,$6e9d2
 move.l #$4c010800,$6e9de
 move.w #$4e71,$6e9e2
 move.l #$4c010800,$6ea30
 move.w #$4e71,$6ea34
extra_done:
 rts
extra_bad:
 lea (error.l,pc),a1
 move.l #2,(a1)
 bra.w FF1ProductionFault
 include "FerrariFormulaOne_Sqrt.s"
modeval: dc.w 8
installed: dc.l 0
error: dc.l 0
ticks: dc.l 0
verified: dc.l 0
cache_api: dc.l 0
cache_old: dc.l 0
cache_called: dc.l 0
candidate: dc.l 0
selection_path: dc.l 2
selection_interval: dc.l 20
 include "FerrariFormulaOne_Profile.s"
 include "FerrariFormulaOne_UpdateHooks.s"

FF1PresentationAfterTick:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 bsr.l B8PoseTick
 tst.w B8DrawEnabled(pc)
 beq.b .done
 lea (schedule_context.l,pc),a0
 bsr.l FF1TimeDue
 tst.l d0
 bne.b .done
 bsr.l B8PrepareRenderCopies
 bsr.l B8Draw
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
B8DrawEnabled: dc.w 1
 include "FerrariFormulaOne_RenderPose.s"
 include "FerrariFormulaOne_RenderHistory.s"
 include "FerrariFormulaOne_RenderOwnership.s"
FF1_FINE_ROAD_PREFETCH equ 1
 include "FerrariFormulaOne_FullPresentation.s"
 include "RenderRoad.s"
 include "RenderFill.s"
 include "RenderClear.s"
 include "RenderGauges.s"
 include "RenderText.s"
 include "RenderBitmap.s"

 FF1UpdateWorkspace

 include "FerrariFormulaOne_NativeExact.s"

 include "RenderColour.s"
 include "FinePause.s"
 include "RenderBlit.s"
 include "FerrariFormulaOne_PublicLifecycle.s"
public_reset_ranges:
 incbin "reset.bin"

public_return: rts
public_bind:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.l #$22f30,(a3)
 bne.w .done
 cmpi.l #2,selection_path(pc)
 bne.w .done
 move.l a4,a2
 move.l $18(a3),d0
 lsl.l #2,d0
 suba.l d0,a2
 lea (public_table.l,pc),a0
 move.l a2,(a0)
 move.l 160*4(a2),d0
 cmp.l public_bound(pc),d0
 beq.w .done
 lea start(pc),a0
 suba.l #FF1_HOST_CODE_SIZE,a0
 move.l FF1_HOST_STACK(a0),d2
 move.l FF1_HOST_STACK+4(a0),d3
 moveq #1,d0
 moveq #2,d1
 bsr.l FF1SelectProfile
 cmpi.l #2,d0
 bne.w .coarse
 ; Qualify every CPU hunk. Slot 46 contains the original Chip-only audio data.
 moveq #0,d5
.qualify:
 cmpi.w #46*4,d5
 beq.b .next
 move.l 0(a2,d5.w),d2
 lsl.l #2,d2
 subq.l #4,d2
 move.l d2,a0
 move.l (a0),d3
 moveq #1,d0
 moveq #2,d1
 bsr.l FF1SelectProfile
 cmpi.l #2,d0
 bne.b .coarse
.next:
 addq.w #4,d5
 cmpi.w #206*4,d5
 blo.b .qualify
 lea start(pc),a0
 lea (public_bindings.l,pc),a1
 bsr.l FF1ApplyBindings
 tst.l d0
 bne.b .bad
 lea (public_bound.l,pc),a0
 move.l 160*4(a2),(a0)
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 move.l FF1_HOST_RESLOAD(a2),a2
 jsr $20(a2)
 bra.b .done
.coarse:
 lea (selection_path.l,pc),a0
 move.l #1,(a0)
 move.l #100,4(a0)
 bra.b .done
.bad:
 lea (public_binding_error.l,pc),a0
 move.l d0,(a0)
 bra.l FF1ProductionFault
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
public_control: dc.w 0
public_table: dc.l 0
public_bound: dc.l 0
public_binding_error: dc.l 0
public_marker: dc.b "FF1FINE",0
 even
 include "FerrariFormulaOne_Bindings.s"
 include "FerrariFormulaOne_PublicMemory.s"
public_bindings:
 incbin "bindings.bin"
