; SPS 0481, 020 + Fast candidate only. Host calls after conversion installers,
; then flushes instruction cache. Native ordering stays 7..0 on the fifth tick.
FF1InstallOpponents:
 movem.l d0-d1/a0,-(sp)
 cmpi.l #$30390003,$671b6
 bne.b .bad
 cmpi.w #$2fbc,$671ba
 bne.b .bad
 cmpi.l #$302efffa,$68da8
 bne.b .bad
 cmpi.l #$0c400007,$68dac
 bne.b .bad
 lea FF1OpponentLoop(pc),a0
 move.w #$4ef9,$671b6
 move.l a0,$671b8
 lea FF1OpponentPairs(pc),a0
 move.w #$4ef9,$68da8
 move.l a0,$68daa
 move.w #$4e71,$68dae
 lea FF1OpponentsInstalled(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #38,(a0)
.done:
 movem.l (sp)+,d0-d1/a0
 rts

FF1OpponentLoop:
 move.w $32fbc,d0
 ble.b .native
 tst.w events_pulse(pc)
 bne.b .native
 ; Jump directly to the player, retaining the native loop exit at index -1.
 clr.w $32fbc
 moveq #0,d0
.native:
 jmp $671bc

FF1OpponentPairs:
 move.w -6(a6),d0
 beq.b .native
 tst.w events_pulse(pc)
 bne.b .native
 ; Outer index zero covers the seven player pairs. The remaining 21 pairs
 ; keep their original order on a native pulse. Retain native post-pair work.
 jmp $69346
.native:
 cmpi.w #7,d0
 jmp $68db0

FF1OpponentsInstalled: dc.l 0
