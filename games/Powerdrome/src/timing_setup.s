; Explicit VERIFY-only deterministic setup inputs. Native initialization and
; random arithmetic still run; natural clock-derived seeding remains default.
 IFNE TIMING_SETUP_SEED+1
timing_setup_begin
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_setup_state(pc),a0
 addq.l #1,12(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 move.w #TIMING_SETUP_SEED,$62(a6)
 move.w #0,$a4(a6)
 bra.w timing_setup_after_begin

timing_setup_reseed
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_setup_state(pc),a0
 addq.l #1,16(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 move.w #TIMING_SETUP_SEED,$62(a6)
 bra.w timing_setup_after_reseed

timing_setup_after_begin dc.w $4ef9
 dc.l 0
timing_setup_after_reseed dc.w $4ef9
 dc.l 0

timing_setup_state dc.b 'PDSETUP1'
 dc.w TIMING_SETUP_SEED
 dc.w 0
 dc.l 0 ; complete native setup entries seeded
 dc.l 0 ; native clock reseeds replaced
 ENDC
