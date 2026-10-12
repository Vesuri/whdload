; SPS 0481 loader patches, resolved by hunk identity rather than allocation order.
; Default-off, 68000-safe. Invoke at the native overlay entry before execution.
 ifnd FF1_PUBLIC_LOADER
FF1_PUBLIC_LOADER equ 0
 endc
 ifne FF1_PUBLIC_LOADER
; A0 = native BPTR hunk table; A1 = original screen-pointer repair callback;
; A2 = original timing callback; D0 = Disable Timing Fix (CUSTOM1).
; Caller has established race HEADER file:$22f30 / entry hunk 160.
; Return D0=0 on success, -1 on unexpected code. D1-D7/A0-A6 preserved.
; All three signatures checked before the first write. Re-entry is harmless.
; Caller flushes instruction cache before returning to the overlay loader.
FF1PatchPublicRace:
 movem.l d1-d3/a0-a5,-(sp)
 move.l d0,d3
 move.l 160*4(a0),d0
 lsl.l #2,d0
 addi.l #4+$ab0,d0
 move.l d0,a3               ; h160 + $ab0, screen-pointer repair
 move.l 184*4(a0),d0
 lsl.l #2,d0
 addi.l #4+$6a,d0
 move.l d0,a4               ; h184 + $6a, SUB.W instead of SUB.L
 move.l 173*4(a0),d0
 lsl.l #2,d0
 addi.l #4+$34,d0
 move.l d0,a5               ; h173 + $34, optional timing fix
 cmpi.l #$e580e580,(a3)
 bne.b .screen_patched
 cmpi.w #$2040,4(a3)
 bne.b .bad
 bra.b .blit
.screen_patched:
 cmpi.w #$4eb9,(a3)
 bne.b .bad
 cmp.l 2(a3),a1
 bne.b .bad
.blit:
 cmpi.w #$9280,(a4)
 beq.b .timing
 cmpi.w #$9240,(a4)
 bne.b .bad
.timing:
 cmpi.l #$e34048c0,(a5)
 bne.b .timing_patched
 cmpi.w #$2840,4(a5)
 bne.b .bad
 bra.b .write
.timing_patched:
 cmpi.w #$4eb9,(a5)
 bne.b .bad
 cmp.l 2(a5),a2
 bne.b .bad
.write:
 move.w #$4eb9,(a3)
 move.l a1,2(a3)
 move.w #$9240,(a4)
 tst.l d3
 bne.b .ok
 move.w #$4eb9,(a5)
 move.l a2,2(a5)
.ok:
 moveq #0,d0
 bra.b .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d1-d3/a0-a5
 rts
 endc
