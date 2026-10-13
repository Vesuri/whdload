; Experimental complete C4 integration: compile-time opt-in, CUSTOM2 gated.
; Capacity is not accepted. The ordinary slave does not include this module.
FF1InstallCoarse200:
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
C4NativeHeading: dc.w 0
C4Enabled: dc.w 1
modeval: dc.w 8
ticks equ C1Heads
 include "FerrariFormulaOne_Coarse200Response.s"
 include "FerrariFormulaOne_Coarse200Return.s"
 include "FerrariFormulaOne_Coarse200Heading.s"
 include "FerrariFormulaOne_Coarse200Timing.s"
 include "FerrariFormulaOne_Coarse200Motion.s"
 include "FerrariFormulaOne_Coarse200Adapters.s"
velocity_records:
velocity_scratch: ds.b 80
