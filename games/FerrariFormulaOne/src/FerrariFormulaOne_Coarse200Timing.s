; Two native-tenth pulses for the experimental 200 ms coarse path.
; Preserve zero-transition eligibility, native phase duty cycles and RNG calls.
; Host supplies relocation, signature failure handling and patch restoration.
C4InstallTiming:
 cmpi.w #$5200,$6712e
 bne.w C1Fault
 cmpi.w #$0200,$67130
 bne.w C1Fault
 cmpi.w #$0003,$67132
 bne.w C1Fault
 cmpi.w #$5340,$67172
 bne.w C1Fault
 cmpi.w #$33c0,$67174
 bne.w C1Fault
 cmpi.w #$0006,$67176
 bne.w C1Fault
 cmpi.w #$6f94,$67178
 bne.w C1Fault
 cmpi.w #$0cb9,$6734e
 bne.w C1Fault
 cmpi.w #$0010,$67350
 bne.w C1Fault
 cmpi.w #$ffff,$67352
 bne.w C1Fault
 cmpi.w #$0006,$67354
 bne.w C1Fault
 cmpi.w #$6c42,$67356
 bne.w C1Fault
 cmpi.w #$3039,$673a4
 bne.w C1Fault
 cmpi.w #$0006,$673a6
 bne.w C1Fault
 cmpi.w #$6f92,$673a8
 bne.w C1Fault
 cmpi.w #$3010,$682c0
 bne.w C1Fault
 cmpi.w #$5340,$682c2
 bne.w C1Fault
 cmpi.w #$3080,$682c4
 bne.w C1Fault
 cmpi.w #$4a79,$6d4f8
 bne.w C1Fault
 cmpi.w #$0003,$6d4fa
 bne.w C1Fault
 cmpi.w #$2fbc,$6d4fc
 bne.w C1Fault
 cmpi.w #$7000,$6d684
 bne.w C1Fault
 cmpi.w #$33c0,$6d686
 bne.w C1Fault
 cmpi.w #$0006,$6d688
 bne.w C1Fault
 cmpi.w #$f13a,$6d68a
 bne.w C1Fault
 cmpi.w #$1039,$6d30a
 bne.w C1Fault
 cmpi.w #$0001,$6d30c
 bne.w C1Fault
 cmpi.w #$be42,$6d30e
 bne.w C1Fault
 cmpi.w #$1039,$6daba
 bne.w C1Fault
 cmpi.w #$0001,$6dabc
 bne.w C1Fault
 cmpi.w #$be42,$6dabe
 bne.w C1Fault
 cmpi.w #$5340,$66838
 bne.w C1Fault
 cmpi.w #$33c0,$6683a
 bne.w C1Fault
 cmpi.w #$0006,$6683c
 bne.w C1Fault
 cmpi.w #$6be0,$6683e
 bne.w C1Fault
 lea C4Phase(pc),a0
 move.w #$4ef9,$6712e
 move.l a0,$67130
 lea C4Countdown(pc),a0
 move.w #$4ef9,$67172
 move.l a0,$67174
 move.w #$4e71,$67178
 lea C4ClutchStart(pc),a0
 move.w #$4ef9,$6734e
 move.l a0,$67350
 move.w #$4e71,$67354
 move.w #$4e71,$67356
 lea C4ClutchEnd(pc),a0
 move.w #$4ef9,$673a4
 move.l a0,$673a6
 lea C4ContactTimer(pc),a0
 move.w #$4ef9,$682c0
 move.l a0,$682c2
 lea C4EventsStart(pc),a0
 move.w #$4ef9,$6d4f8
 move.l a0,$6d4fa
 lea C4EventsEnd(pc),a0
 move.w #$4ef9,$6d684
 move.l a0,$6d686
 move.w #$4e71,$6d68a
 lea C4AccelGate(pc),a0
 move.w #$4ef9,$6d30a
 move.l a0,$6d30c
 lea C4DragGate(pc),a0
 move.w #$4ef9,$6daba
 move.l a0,$6dabc
 lea C4FlagTimer(pc),a0
 move.w #$4ef9,$66838
 move.l a0,$6683a
 move.w #$4e71,$6683e
 rts
C4Phase:
 addq.b #2,d0
 andi.b #3,d0
 movem.l d0-d1/a0,-(sp)
; Native MOVE.B leaves the upper D0 bits live; the helper takes a word.
C4PhaseNormalize equ *
 andi.l #3,d0
 move.w $6f272,d1
 bsr.w FF1PhasePulses200
 lea C4PhaseWeight(pc),a0
 move.w d0,(a0)
 movem.l (sp)+,d0-d1/a0
 jmp $67134
; Native callers own the zero-entry guards (contact also rejects negatives).
; Keep the zero-transition stop here: decrementing twice unconditionally would
; turn an expiring value of one into -1. Q01 checks 88 installed caller cases.
C4Countdown:
 subq.w #1,d0
 beq.b .store
 subq.w #1,d0
.store:
 move.w d0,$66f94
 jmp $6717a
C4ContactTimer:
 move.w (a0),d0
 subq.w #1,d0
 beq.b .store
 subq.w #1,d0
.store:
 move.w d0,(a0)
 jmp $682c6
C4ClutchStart:
 move.l a0,-(sp)
 lea C4ClutchLeft(pc),a0
 move.w #2,(a0)
 move.l (sp)+,a0
C4ClutchRun:
 cmpi.l #$10ffff,$66c42
 jmp $67358
C4ClutchEnd:
 move.l a0,-(sp)
 lea C4ClutchLeft(pc),a0
 subq.w #1,(a0)
 move.l (sp)+,a0
 bne.b C4ClutchRun
 move.w $66f92,d0
 jmp $673aa
C4EventsStart:
 move.l a0,-(sp)
 lea C4EventsLeft(pc),a0
 move.w #2,(a0)
 move.l (sp)+,a0
; Re-enter native eligibility for each pulse: a first-pulse failure may make
; the second pulse ineligible. Never hoist the status tests or combine RNG calls.
; Q01: native two-call oracle covers all cars, component/tyre failures, signed
; status guards and exact RNG state/count (420 cases on A500 and A500+Fast).
C4EventsRun:
 tst.w $32fbc
 jmp $6d4fe
C4EventsEnd:
 move.l a0,-(sp)
 lea C4EventsLeft(pc),a0
 subq.w #1,(a0)
 move.l (sp)+,a0
 bne.b C4EventsRun
 moveq #0,d0
 move.w d0,$6f13a
 jmp $6d68c
C4AccelGate:
 move.w C4PhaseWeight(pc),d0
 beq.b .skip
 jmp $6d336
.skip:
 jmp $6d44e
C4DragGate:
 move.w C4PhaseWeight(pc),d0
 beq.b .skip
 jmp $6daee
.skip:
 jmp $6dae4
C4FlagTimer:
 subq.w #1,d0
 beq.b .store
 subq.w #1,d0
.store:
 move.w d0,$66be0
 jmp $66840
C4PhaseWeight: dc.w 2
C4ClutchLeft: dc.w 0
C4EventsLeft: dc.w 0
