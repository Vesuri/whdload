; WHDLoad-side selection runs before KickEmu boot. The expansion allocation
; and WHDLoad ATTNFLAGS are authoritative; guest Exec is not used to select Fast.
 include "payloads.i"
FF1ProductionBoot:
 movem.l d0-d7/a0-a6,-(sp)
 move.l a0,a2
 lea FF1ProfileTags(pc),a0
 jsr resload_Control(a2)
 move.l FF1ProfileCustom2(pc),d0
 move.l FF1ProfileAttn(pc),d1
 move.l _expmem(pc),d2
 move.l #$c0000,d3
 bsr.w FF1SelectProfile
 lea FF1ProfileMode(pc),a0
 move.l d0,(a0)
 movem.l (sp)+,d0-d7/a0-a6
 lea _boot(pc),a1
 jmp (a1)
FF1ProfileTags:
 dc.l WHDLTAG_ATTNFLAGS_GET
FF1ProfileAttn: dc.l 0
 dc.l WHDLTAG_CUSTOM2_GET
FF1ProfileCustom2: dc.l 0
 dc.l WHDLTAG_MONITOR_GET
FF1ProfileMonitor: dc.l 0
 dc.l TAG_DONE
FF1ProfileMode: dc.l 0
 include "FerrariFormulaOne_Profile.s"
FF1Dispatch:
 movem.l d0-d7/a0-a6,-(sp)
 move.l FF1ProfileMode(pc),d1
 cmpi.l #2,d1
 bne.b .coarse
 lea _expmem-32(pc),a5
 adda.l #FF1_FINE_OFFSET,a5
 jsr (a5)
 ; Failed Fast ownership qualification selects the supported chip-only path.
 cmpi.l #2,FF1_FINE_SELECTION(a5)
 beq.b .done
.coarse:
 lea _expmem-32(pc),a5
 move.l FF1ProfileAttn(pc),d1
 btst #1,d1
 beq.b .m000
 adda.l #FF1_020_OFFSET,a5
 bra.b .call
.m000:
 adda.l #FF1_000_OFFSET,a5
.call:
 jsr (a5)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
FF1WrongVersion:
 pea (TDREASON_WRONGVER).w
 bra.w EXIT

FF1PerformanceAbort:
 pea .message(pc)
 pea (TDREASON_FAILMSG).w
 bra.w EXIT
.message:
 dc.b "Performance mode could not safely initialise or continue.",0
 even

FF1RequirePAL:
 pea (TDREASON_MUSTPAL).w
 bra.w EXIT
