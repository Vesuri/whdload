; Ferrari Formula One: normal-mode curvature lookahead.
; A0 = signed-word curvature table, D0.l = segment, D1.l = segment count.
; Caller must validate 12 <= count <= 32767 and 0 <= segment < count.
; Return D0.l = abs(sum of ten samples starting at segment+2, with wrap).
; D1/A0/CCR scratch; other registers preserved. 68000 compatible.
; This is the value contract of the single inspected SPS C caller; it does
; not promise the native routine's incidental scratch-register/stack writes.
; The alternate track mode must retain its separate native behavior.
FF1TrackLookaheadNormal:
        movem.l d2-d3/a1,-(sp)
        move.l  d1,d2
        add.l   d2,d2
        move.l  a0,a1
        adda.l  d2,a1
        addq.l  #2,d0
        cmp.l   d1,d0
        blo.b   .start
        sub.l   d1,d0
.start: add.l   d0,d0
        adda.l  d0,a0
        moveq   #0,d0
        moveq   #9,d3
.loop:  move.w  (a0)+,d1
        ext.l   d1
        add.l   d1,d0
        cmpa.l  a1,a0
        blo.b   .next
        suba.l  d2,a0
.next:  dbra    d3,.loop
        tst.l   d0
        bpl.b   .done
        neg.l   d0
.done:  movem.l (sp)+,d2-d3/a1
        rts
