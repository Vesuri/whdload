; Ferrari Formula One: fixed-interval time accounting.
;
; PAL calibration: 3546895 / 71051 fields/second. One time unit is
; 1/35468950 second, so a field is exactly 710510 units and 20 ms is
; exactly 709379 units. Do not substitute one VBL for one 20 ms tick.
;
; This module does not install hooks or enable the performance mode.
; The caller owns CPU selection, native logic conversions, input history,
; overlay lifetime and safe presentation. A 200 ms interval is a test
; candidate for 68000, not an accepted performance configuration.
;
; A0 points to an FF1T_SIZE-byte context. All entry points are 68000-safe.
; Field is called by a single VBL producer. Other calls are made by the
; game task. Initialise before installing the producer; never initialise
; a live context. Rebase does not stop the monotonic producer clock.
; D0-D3/A1 are scratch. Other registers and A0 are preserved.

FF1T_FIELDS     equ 0
FF1T_ELAPSED_HI equ 4
FF1T_ELAPSED_LO equ 8
FF1T_CONSUMED_HI equ 12
FF1T_CONSUMED_LO equ 16
FF1T_INTERVAL   equ 20
FF1T_TICKS      equ 24
FF1T_PHASE_MS   equ 28
FF1T_STEP_MS    equ 30
FF1T_REBASES    equ 32
FF1T_REBASED_HI equ 36
FF1T_REBASED_LO equ 40
FF1T_PAUSED     equ 44
FF1T_PAUSE_HI   equ 48
FF1T_PAUSE_LO   equ 52
FF1T_SIZE       equ 56
FF1T_FIELD_UNITS equ 710510
FF1T_20MS_UNITS equ 709379

; D0.w interval in milliseconds: 20 or provisional 200.
; D0.l returns 1 for success, 0 for unsupported interval (context unchanged).
FF1TimeInit:
        cmpi.w  #20,d0
        beq.b   .fine
        cmpi.w  #200,d0
        bne.b   .unsupported
        move.l  #FF1T_20MS_UNITS*10,d2
        bra.b   .clear
.fine:  move.l  #FF1T_20MS_UNITS,d2
.clear: move.w  d0,d3
        move.l  a0,a1
        moveq   #FF1T_SIZE/4-1,d1
.zero:  clr.l   (a1)+
        dbra    d1,.zero
        move.l  d2,FF1T_INTERVAL(a0)
        move.w  d3,FF1T_STEP_MS(a0)
        moveq   #1,d0
        rts
.unsupported:
        moveq   #0,d0
        rts

; Single producer. The enclosing interrupt hook must preserve its ABI/CCR.
FF1TimeField:
        addq.l  #1,FF1T_FIELDS(a0)
        addi.l  #FF1T_FIELD_UNITS,FF1T_ELAPSED_LO(a0)
        bcc.b   .done
        addq.l  #1,FF1T_ELAPSED_HI(a0)
.done:  rts

; Coherent monotonic timestamp in D2:D1, even if a VBL interrupts this read.
FF1TimeSnapshot:
.retry: move.l  FF1T_ELAPSED_HI(a0),d2
        move.l  FF1T_ELAPSED_LO(a0),d1
        cmp.l   FF1T_ELAPSED_HI(a0),d2
        bne.b   .retry
        rts

; D0 = 1 if one complete tick is due, otherwise 0. D2:D1 = pending units.
; Only completed simulation work advances CONSUMED. Drawing cannot erase debt.
FF1TimeDue:
        tst.l   FF1T_PAUSED(a0)
        beq.b   .active
        move.l  FF1T_PAUSE_HI(a0),d2
        move.l  FF1T_PAUSE_LO(a0),d1
        bra.b   .pending
.active:
        bsr.b   FF1TimeSnapshot
.pending:
        sub.l   FF1T_CONSUMED_LO(a0),d1
        move.l  FF1T_CONSUMED_HI(a0),d3
        subx.l  d3,d2
        tst.l   FF1T_PAUSED(a0)
        bne.b   .no
        tst.l   d2
        bne.b   .yes
        cmp.l   FF1T_INTERVAL(a0),d1
        bcs.b   .no
.yes:   moveq   #1,d0
        rts
.no:    moveq   #0,d0
        rts

; Commit ONE completed tick. Returns D0 = native tenth-second pulses (0..2).
; Calling before a tick is due returns -1 without advancing consumed time.
; Clock eligibility/countdown/modal rules must still be applied by the caller.
FF1TimeConsume:
        bsr.w   FF1TimeDue
        tst.l   d0
        beq.b   .early
        move.l  FF1T_INTERVAL(a0),d0
        add.l   d0,FF1T_CONSUMED_LO(a0)
        bcc.b   .count
        addq.l  #1,FF1T_CONSUMED_HI(a0)
.count: addq.l  #1,FF1T_TICKS(a0)
        move.w  FF1T_STEP_MS(a0),d1
        add.w   FF1T_PHASE_MS(a0),d1
        moveq   #0,d0
.pulse: cmpi.w  #100,d1
        bcs.b   .store
        subi.w  #100,d1
        addq.l  #1,d0
        bra.b   .pulse
.store: move.w  d1,FF1T_PHASE_MS(a0)
        rts
.early: moveq   #-1,d0
        rts

; Pause excludes only wall time between these calls. Existing active debt,
; including a partial simulation interval, survives. Repeated calls are no-ops.
; D0 returns 1 for a transition, 0 when already in the requested state.
FF1TimePause:
        tst.l   FF1T_PAUSED(a0)
        bne.b   .unchanged
        bsr.w   FF1TimeSnapshot
        move.l  d2,FF1T_PAUSE_HI(a0)
        move.l  d1,FF1T_PAUSE_LO(a0)
        moveq   #1,d0
        move.l  d0,FF1T_PAUSED(a0)
        rts
.unchanged:
        moveq   #0,d0
        rts

FF1TimeResume:
        tst.l   FF1T_PAUSED(a0)
        beq.b   .unchanged
        bsr.w   FF1TimeSnapshot
        sub.l   FF1T_PAUSE_LO(a0),d1
        move.l  FF1T_PAUSE_HI(a0),d3
        subx.l  d3,d2
        bsr.b   FF1TimeExclude
        clr.l   FF1T_PAUSED(a0)
        clr.l   FF1T_PAUSE_HI(a0)
        clr.l   FF1T_PAUSE_LO(a0)
        moveq   #1,d0
        rts
.unchanged:
        moveq   #0,d0
        rts

; Explicit reset of pending time for loading or a new driving epoch. The
; discarded amount is counted. Use Pause/Resume for a reversible pause;
; never call Rebase as a catch-up/overload policy. Clock phase is preserved.
FF1TimeRebase:
        bsr.w   FF1TimeSnapshot
        tst.l   FF1T_PAUSED(a0)
        beq.b   .pending
        move.l  d2,FF1T_PAUSE_HI(a0)
        move.l  d1,FF1T_PAUSE_LO(a0)
.pending:
        sub.l   FF1T_CONSUMED_LO(a0),d1
        move.l  FF1T_CONSUMED_HI(a0),d3
        subx.l  d3,d2
FF1TimeExclude:
        move.l  FF1T_REBASED_HI(a0),d3
        add.l   d1,FF1T_REBASED_LO(a0)
        addx.l  d2,d3
        move.l  d3,FF1T_REBASED_HI(a0)
        move.l  FF1T_CONSUMED_HI(a0),d3
        add.l   d1,FF1T_CONSUMED_LO(a0)
        addx.l  d2,d3
        move.l  d3,FF1T_CONSUMED_HI(a0)
        addq.l  #1,FF1T_REBASES(a0)
        rts
