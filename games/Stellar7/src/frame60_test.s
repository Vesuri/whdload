        IFD VERIFY
        IFD FRAME_TEST
; Draw exactly the requested completed simulation tick, then hold gameplay
; while interrupts/display scan continue. The capture can inspect settled
; displayed fields instead of comparing pictures from different game ticks.
; This diagnostic intentionally requires the harness to quit the emulator.
s60_frame_results: dc.b 'V760'
        dc.l 0,0 ; completed tick, rendering-finished flag
s60_test_frame:
        move.l (s60_ticks-s60_last,a2),d0
        cmp.l #FRAME_TEST,d0
        bne .done
        move.w #1,(s60_rendering-s60_last,a2)
        bsr s60_render
        clr.w (s60_rendering-s60_last,a2)
        lea (s60_frame_results,pc),a0
        move.l (s60_ticks-s60_last,a2),(4,a0)
        move.l #1,(8,a0)
.hold:  bra.s .hold
.done:  rts
        ENDC
        ENDC
