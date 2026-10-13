; Exact floor sqrt for 2^48 <= unsigned D1:D0 < 2^50.
; The caller retains its exact full-domain fallback. Preserve D1-D7/A0-A6.
; i=N>>38; s=floor(sqrt(i<<20)); r=s<<9 <= floor(sqrt(N)).
; R=N-r*r, q=floor(R/(2*r)) = floor((R>>10)/s).
; For delta=floor(sqrt(N))-r, R>=2*r*delta+delta^2, hence q>=delta.
; s>=32768 and R<9*2^35, so the DIVU numerator fits and q<9216.
; E=N-(r+q)^2 = R-2*r*q-q*q lies in [-q*q,2*r).
; Both bounds fit signed 32 bits, so its low longword is the exact signed E.
; Correct a negative E by E+=2*(r+q)-1 and decrement the estimate. No rounding
; or truncation of the input occurs; the returned estimate is floor(sqrt(N)).
FF1C4SeededRoot:
 movem.l d1-d5/a0,-(sp)
 move.l d0,d5
 move.l d1,d3
 move.l d1,d2
 lsr.l #6,d2
 add.w d2,d2
 lea C4RootSeedControl(pc),a0
 ; Fixed long encoding preserves host binding offsets across assembly passes.
 dc.w $d1fc                 ; adda.l #biased table displacement,a0
 dc.l C4RootSeeds-C4RootSeedControl-2048
 moveq #0,d4
 move.w (a0,d2.w),d4
 move.l d4,d2
 mulu.w d4,d2
 ; r*r = s*s << 18; form the full unsigned remainder R.
 move.l d2,d0
 swap d0
 clr.w d0
 lsl.l #2,d0
 rol.l #2,d2
 swap d2
 andi.l #$3ffff,d2
 sub.l d0,d5
 subx.l d2,d3
 ; Exact floor(R/(s<<10)), using one non-overflowing word DIVU.
 move.l d5,d0
 lsr.l #8,d0
 lsr.l #2,d0
 move.l d3,d1
 swap d1
 clr.w d1
 lsl.l #6,d1
 or.l d1,d0
 divu.w d4,d0
 moveq #0,d2
 move.w d0,d2
 ; E's signed range proves that only the low longword is needed here.
 move.l d2,d1
 mulu.w d2,d1
 move.l d4,d0
 mulu.w d2,d0
 lsl.l #8,d0
 lsl.l #2,d0
 add.l d1,d0
 sub.l d0,d5
 lsl.l #8,d4
 add.l d4,d4
 add.l d2,d4
 tst.l d5
 bpl.b .done
.down:
 move.l d4,d2
 add.l d2,d2
 subq.l #1,d2
 add.l d2,d5
 subq.l #1,d4
 tst.l d5
 bmi.b .down
.done:
 move.l d4,d0
 movem.l (sp)+,d1-d5/a0
 rts
C4RootSeedControl: dc.w 0
