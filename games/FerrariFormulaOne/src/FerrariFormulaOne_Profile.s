; Default-off profile selection, callable on 68000.
; D0.l = CUSTOM2, D1.l = WHDLoad ATTNFLAGS, D2.l = WHDLoad ws_ExpMem
; allocation address, D3.l = allocation size. Never use guest Exec to detect RAM.
; Returns D0.l: 0 legacy, 1 native 100 ms, 2 player 20 ms / opponents 100 ms.
; D1.l: interval in ms (0 for legacy). D2-D7/A0-A6 preserved; CCR scratch.
; This selects a candidate, not permission to enable an unvalidated path.
; Fast address qualification is conservative: complete allocation must lie in
; Zorro-II RAM [$200000,$a00000) or the 32-bit expansion range [$1000000,...).
; Unknown/chip/slow/empty/wrapping allocations fall back to native 100 ms.
FF1SelectProfile:
        tst.l   d0
        beq.b   .legacy
        btst    #1,d1                   ; AFB_68020 from WHDLoad, not guest Exec
        beq.b   .coarse
        tst.l   d3
        beq.b   .coarse
        move.l  d4,-(sp)
        move.l  d2,d4
        add.l   d3,d4
        bcs.b   .reject
        cmpi.l  #$200000,d2
        blo.b   .reject
        cmpi.l  #$1000000,d2
        bhs.b   .fine
        cmpi.l  #$a00000,d4
        bhi.b   .reject
.fine:  move.l  (sp)+,d4
        moveq   #2,d0
        moveq   #20,d1
        rts
.reject:
        move.l  (sp)+,d4
.coarse:
        moveq   #1,d0
        moveq   #100,d1
        rts
.legacy:
        moveq   #0,d0
        moveq   #0,d1
        rts
