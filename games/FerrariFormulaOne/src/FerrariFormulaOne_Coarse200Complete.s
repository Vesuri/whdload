; Experimental complete C4 integration: compile-time opt-in, CUSTOM2 gated.
; Capacity is not accepted. The ordinary slave does not include this module.
FF1InstallCoarse200:
 bsr.w FF1Coarse200Reset
 IFD FF1_C4_BOUNDARY_P5
 bsr.w FF1C4BoundaryInit
 ENDC
 bsr.w FF1InstallMultiplyNative200
 bsr.w FF1Coarse200ProjectionSkip
 bsr.w FF1Coarse200ReturnSkip
 moveq #8,d0
 bsr.w install_velocity
 bsr.w install_position_bridge
 bsr.w install_fine_position
 move.w C4NativeHeading(pc),-(sp)
 tst.w (sp)+
 beq.b .fine_heading
 bsr.w FF1InstallCoarse200Heading
 bra.b .heading_done
.fine_heading:
 bsr.w install_heading
.heading_done:
 bsr.w install_steering
 bsr.w install_wear
 bsr.w install_fuel
 bsr.w C4InstallTiming
 bsr.w FF1Coarse200ResponseSkip
 move.l error(pc),d0
 bne.w C1Fault
 rts
; Activation follows 125 native updates on every newly bound race. Discard
; previous-race ownership; velocity_load seeds each car from its native values.
; bridge_load replaces integer position words but deliberately keeps fractions,
; so those fractions must start empty when ownership is acquired again.
FF1Coarse200Reset:
 IFD FF1_RESET200_AB
 move.w FF1Reset200Control(pc),-(sp)
 tst.w (sp)+
 bne.b .done
 ENDC
 movem.l d0/a0,-(sp)
 lea velocity_initialized(pc),a0
 clr.w (a0)
 lea position_shadow(pc),a0
 moveq #23,d0
.clear:
 clr.l (a0)+
 dbra d0,.clear
 movem.l (sp)+,d0/a0
.done:
 rts
 IFD FF1_RESET200_AB
FF1Reset200Control: dc.w 0
 ENDC
C4NativeHeading: dc.w 0
C4Enabled: dc.w 1
modeval: dc.w 8
ticks equ C1Heads
 include "FerrariFormulaOne_NativeMultiply200.s"
 include "FerrariFormulaOne_Coarse200Projection.s"
 include "FerrariFormulaOne_Coarse200Response.s"
 include "FerrariFormulaOne_Coarse200Return.s"
 include "FerrariFormulaOne_Coarse200Heading.s"
 include "FerrariFormulaOne_Coarse200Timing.s"
 include "FerrariFormulaOne_Coarse200Motion.s"
 include "FerrariFormulaOne_Coarse200Adapters.s"
velocity_records:
velocity_scratch: ds.b 80
