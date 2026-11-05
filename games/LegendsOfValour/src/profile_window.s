; Capture-only DOS metadata handshake for Barto's qOffsets profiler window.
; Invoked in the tape's VBL context. Keep interrupts masked while paused with
; temporary metadata; restore every byte and the original SR before the trace.
_profile_prepare
        movem.l d0-a6,-(sp)
        lea (_profile_state,pc),a6
        move.w sr,(a6)
        ori.w #$0700,sr
        move.l ($4).w,a0
        move.l (276,a0),a0        ; ExecBase.ThisTask
        cmp.b #13,(8,a0)          ; NT_PROCESS
        bne .bad
        move.l a0,(2,a6)
        move.l (128,a0),(6,a6)   ; Process.pr_SegList
        move.l (140,a0),(10,a6)  ; Process.pr_TaskNum
        lea ($1000).w,a1
        lea (14,a6),a2
        moveq #7,d0
.save   move.l (a1)+,(a2)+
        dbf d0,.save
        move.l #1,($1000).w
        clr.l ($1004).w
        clr.l ($1008).w
        move.l #$405,($100c).w   ; array entry -> synthetic segment at $1014
        move.l #$80000003,($1010).w ; qOffsets subtracts four: size $7fffffff
        clr.l ($1014).w
        move.l #$400,(128,a0)    ; temporary segment-list array BPTR
        clr.l (140,a0)          ; bypass CLI segment-list override
        movem.l (sp)+,d0-a6
        rts
.bad    lea (_profile_badmsg,pc),a0
        bra _c2p_abort
_profile_restore
        movem.l d0-a6,-(sp)
        lea (_profile_state,pc),a6
        move.l (2,a6),a0
        move.l (6,a6),(128,a0)
        move.l (10,a6),(140,a0)
        lea ($1000).w,a1
        lea (14,a6),a2
        moveq #7,d0
.copy   move.l (a2)+,(a1)+
        dbf d0,.copy
        movem.l (sp)+,d0-a6
        move.w (_profile_state,pc),sr
        rts
_profile_badmsg dc.b "PROFILE: current task is not a DOS process",0
        EVEN
_profile_state ds.b 46
