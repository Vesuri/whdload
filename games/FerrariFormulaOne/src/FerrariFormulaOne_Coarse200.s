; SPS 0481 68000 200 ms conversion integration, opt-in and under construction.
; Stage 1 wires the four continuous heading increments. It does NOT select a
; 200 ms gameplay interval: velocity, rates and event cadence must be integrated
; before that is allowed. The host owns relocation, signature checks, interrupt
; exclusion, patch-ledger restoration, cache flush and public memory lifetime.
 IFD FF1_COARSE_200
 IFD FF1_COARSE_020
 fail "FF1_COARSE_200 requires the 68000 host"
 ENDC
FF1InstallCoarse200:
 include "FerrariFormulaOne_Coarse200Heading.s"
C4Enabled: dc.w 1
 ENDC
