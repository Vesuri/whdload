; FF1_PLAYER_HOOKS uses cursor.b at +10; byte +11 belongs to fuel and
; must survive both sampling and reset. History and quantum fields are unchanged.
; Fine controller history: sample raw steering every 20 ms, retain the native
; two-tap mean with a 100 ms (five-quantum) separation. Native word addition
; wraps before arithmetic shift, matching the original filter arithmetic.
; Per-car MEMF_PUBLIC state: history[5].w, cursor.w, last_quantum.l, last_raw.w.
; D3.l is the simulation quantum serial, not a frame/VBL or controller-call count.
; Inactive gaps hold the last raw request; reset explicitly at cold/recovery
; initialization. All instructions are 68000-safe; production scheduling is not
; supplied by this helper.

; D0.w initial raw steering, D3.l preceding/current reset quantum, A0 state.
; All registers preserved, CCR scratch.
FF1SteeringReset:
        move.w  d0,(a0)
        move.w  d0,2(a0)
        move.w  d0,4(a0)
        move.w  d0,6(a0)
        move.w  d0,8(a0)
 IFD FF1_PLAYER_HOOKS
        clr.b   10(a0)
 ELSE
        clr.w   10(a0)
 ENDC
        move.l  d3,12(a0)
        move.w  d0,16(a0)
        rts

; D0.w current raw, D3.l current quantum, A0 state.
; D0.l filtered request, D2.l request 100 ms earlier, D1.l status 0/-1.
; Invalid cursor, duplicate quantum or backwards interval >=2^31: unchanged
; state and D0, D2 unspecified. D3-D7/A0-A6 preserved; CCR scratch.
FF1SteeringSample20:
        movem.l d4-d6,-(sp)
        moveq   #0,d5
 IFD FF1_PLAYER_HOOKS
        move.b  10(a0),d5
 ELSE
        move.w  10(a0),d5
 ENDC
        cmpi.w  #4,d5
        bhi.w   .bad
        move.l  d3,d4
        sub.l   12(a0),d4
        tst.l   d4             ; test modular delta, independent of SUB overflow
        ble.w   .bad
        cmpi.l  #5,d4
        blo.b   .fill_gap
        move.w  16(a0),d6
        move.w  d6,(a0)
        move.w  d6,2(a0)
        move.w  d6,4(a0)
        move.w  d6,6(a0)
        move.w  d6,8(a0)
        moveq   #0,d5
        bra.b   .sample
.fill_gap:
        subq.w  #1,d4
        beq.b   .sample
        move.w  d5,d6
        add.w   d6,d6
        move.w  16(a0),(a0,d6.w)
        addq.w  #1,d5
        cmpi.w  #5,d5
        bne.b   .fill_gap
        moveq   #0,d5
        bra.b   .fill_gap
.sample:
        move.w  d5,d6
        add.w   d6,d6
        move.w  (a0,d6.w),d2
        ext.l   d2
        move.w  d0,(a0,d6.w)
        move.w  d0,16(a0)
        move.l  d3,12(a0)
        addq.w  #1,d5
        cmpi.w  #5,d5
        bne.b   .cursor
        moveq   #0,d5
.cursor:
 IFD FF1_PLAYER_HOOKS
        move.b  d5,10(a0)
 ELSE
        move.w  d5,10(a0)
 ENDC
        add.w   d2,d0
        asr.w   #1,d0
        ext.l   d0
        moveq   #0,d1
        bra.b   .done
.bad:
        moveq   #-1,d1
.done:
        movem.l (sp)+,d4-d6
        rts
