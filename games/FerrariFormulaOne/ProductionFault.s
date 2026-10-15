; Leave WHDLoad cleanly if a production invariant or immutable signature fails.
; Diagnostic builds retain their breakpoint loops for the local harness.
FF1ProductionFault:
 IFD FF1_FINE_BLIT_OWNER
 bsr.l FF1FineBlitRestore
 ENDC
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 adda.l #FF1_HOST_ABORT,a2
 jmp (a2)
