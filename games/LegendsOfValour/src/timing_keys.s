; VERIFY/TIMING_STUDY only, CUSTOM5 bit 24: inject raw-key events through
; input.device from an Exec task. VBL only signals; device IO never runs there.
; This exercises console keymap conversion and the real outstanding read.
        INCLUDE "exec/tasks.i"
        INCLUDE "devices/input.i"
        INCLUDE "devices/inputevent.i"
        INCLUDE "lvo/intuition_lib.i"
TK_STACK = (TC_SIZE+3)&$fffffffc
TK_BYTES = TK_STACK+4096
_timing_keys_install
        move.l (_custom5,pc),d0
        btst #24,d0
        beq .done
        IFD TIMING_KEYS_TEXT
        ; Observe the native save-panel console poll; preserve its real caller.
        move.l (_hunks+8*4,pc),a0
        cmp.w #$4ef9,($800,a0)
        bne .bad
        move.l (_hunks+4,pc),a1
        lea ($1eb6,a1),a1
        cmp.l ($802,a0),a1
        bne .bad
        lea (_timing_keys_text_original,pc),a2
        move.l a1,(a2)
        lea (_timing_keys_text_poll,pc),a1
        move.l a1,($802,a0)
        ENDC
        move.l 4.w,a6
        move.l #TK_BYTES,d0
        move.l #MEMF_PUBLIC+MEMF_CLEAR,d1
        jsr (_LVOAllocMem,a6)
        tst.l d0
        beq .bad
        lea (_timing_keys_task,pc),a0
        move.l d0,(a0)
        move.l d0,a2
        move.b #NT_TASK,LN_TYPE(a2)
        move.b #10,LN_PRI(a2)
        lea (_timing_keys_name,pc),a0
        move.l a0,LN_NAME(a2)
        lea TK_STACK(a2),a0
        move.l a0,TC_SPLOWER(a2)
        adda.l #4096,a0
        move.l a0,TC_SPUPPER(a2)
        move.l a0,TC_SPREG(a2)
        lea TC_MEMENTRY(a2),a0
        lea LH_TAIL(a0),a1
        move.l a1,LH_HEAD(a0)
        move.l a0,LH_TAILPRED(a0)
        move.l a2,a1
        lea (_timing_keys_worker,pc),a2
        suba.l a3,a3
        jsr (_LVOAddTask,a6)
.done   rts
.bad    lea (_timing_keys_error,pc),a0
        move.w #1,(a0)
        rts

_timing_keys_wake
        movem.l d0/a0-a1/a6,-(sp)
        move.l (_timing_keys_signal,pc),d0
        beq .done
        move.l (_timing_keys_task,pc),a1
        move.l 4.w,a6
        jsr (_LVOSignal,a6)
.done   movem.l (sp)+,d0/a0-a1/a6
        rts

_timing_keys_worker
        move.l 4.w,a6
        moveq #-1,d0
        jsr (_LVOAllocSignal,a6)
        tst.l d0
        bmi .bad
        lea (_timing_keys_port,pc),a2
        move.b d0,MP_SIGBIT(a2)
        move.b #NT_MSGPORT,LN_TYPE(a2)
        move.l (_timing_keys_task,pc),MP_SIGTASK(a2)
        lea MP_MSGLIST(a2),a0
        lea LH_TAIL(a0),a1
        move.l a1,LH_HEAD(a0)
        move.l a0,LH_TAILPRED(a0)
        lea (_timing_keys_io,pc),a1
        move.l a2,MN_REPLYPORT(a1)
        move.w #IOSTD_SIZE,MN_LENGTH(a1)
        lea (_timing_keys_device,pc),a0
        moveq #0,d0
        moveq #0,d1
        jsr (_LVOOpenDevice,a6)
        tst.l d0
        bne .bad
        lea (_timing_keys_intuition_name,pc),a1
        moveq #0,d0
        jsr (_LVOOpenLibrary,a6)
        tst.l d0
        beq .bad
        move.l d0,a5
        moveq #-1,d0
        jsr (_LVOAllocSignal,a6)
        tst.l d0
        bmi .bad
        move.l d0,d6
        moveq #1,d1
        lsl.l d0,d1
        lea (_timing_keys_signal,pc),a0
        move.l d1,(a0)
        lea (_timing_keys_schedule,pc),a4
        IFD TIMING_KEYS_TEXT
        lea (_timing_keys_text_schedule,pc),a4
        ENDC
        move.l (_custom5,pc),d0
        btst #30,d0
        beq .schedule
        lea (_timing_keys_combat_schedule,pc),a4
.schedule
        moveq #0,d7
.wait   move.l (_timing_keys_signal,pc),d0
        jsr (_LVOWait,a6)
.next   move.l (_timing_study_watch_fields,pc),d0
        move.w (a4),d1
        IFD TIMING_KEYS_TEXT
        move.l (_timing_keys_text_firstfield,pc),d2
        beq .wait
        move.l (_h11,pc),a0
        move.l ($602c,a0),d0
        sub.l d2,d0
        bra .due
        ENDC
        move.l (_custom5,pc),d2
        btst #30,d2
        beq .ordinary_time
        move.l (_timing_combat_firstfield,pc),d2
        beq .wait
        move.l (_h11,pc),a0
        move.l ($602c,a0),d0
        sub.l d2,d0
        bra .due
.ordinary_time
        btst #25,d2
        beq .due
        add.w #56,d1                ; force the blocking reader to wait
.due    cmp.w d1,d0
        bcs .wait
        lea (_timing_keys_event,pc),a0
        moveq #ie_SIZEOF/2-1,d0
.clear  clr.w (a0)+
        dbf d0,.clear
        lea (_timing_keys_event,pc),a2
        move.b #IECLASS_RAWKEY,ie_Class(a2)
        move.w (2,a4),ie_Code(a2)
        move.w (4,a4),ie_Qualifier(a2)
        ; Kickstart 1.3 does not fill IND_WRITEEVENT timestamps for us.
        lea ie_TimeStamp(a2),a0
        lea 4(a0),a1
        move.l a5,a6
        jsr (_LVOCurrentTime,a6)
        move.l 4.w,a6
        lea (_timing_keys_io,pc),a1
        move.w #IND_WRITEEVENT,IO_COMMAND(a1)
        move.l #ie_SIZEOF,IO_LENGTH(a1)
        move.l a2,IO_DATA(a1)
        jsr (_LVODoIO,a6)
        tst.l d0
        bne .bad
        lea (_timing_keys_sent,pc),a0
        addq.l #1,(a0)
        lea 6(a4),a4
        addq.w #1,d7
        moveq #7,d1
        move.l (_custom5,pc),d0
        btst #30,d0
        beq .ansi_option
        moveq #2,d1
        bra .event_count
.ansi_option
        btst #27,d0
        beq .event_count
        moveq #9,d1
.event_count
        IFD TIMING_KEYS_TEXT
        moveq #11,d1
        ENDC
        cmp.w d1,d7
        bcs .next
        lea (_timing_keys_signal,pc),a0
        clr.l (a0)
        move.l d6,d0
        jsr (_LVOFreeSignal,a6)
        lea (_timing_keys_io,pc),a1
        jsr (_LVOCloseDevice,a6)
        move.l a5,a1
        jsr (_LVOCloseLibrary,a6)
        moveq #0,d0
        lea (_timing_keys_port,pc),a0
        move.b MP_SIGBIT(a0),d0
        jsr (_LVOFreeSignal,a6)
        lea (_timing_keys_done,pc),a0
        move.w #1,(a0)
        suba.l a1,a1
        jmp (_LVORemTask,a6)
.bad    lea (_timing_keys_error,pc),a0
        move.w #1,(a0)
        lea (_timing_keys_signal,pc),a0
        clr.l (a0)
        suba.l a1,a1
        jmp (_LVORemTask,a6)

_timing_keys_combat_schedule
        dc.w 24,$40,0, 26,$c0,0    ; space down/up relative to combat entry
_timing_keys_schedule
        dc.w 8,$20,0, 10,$a0,0       ; a down/up
        dc.w 20,$35,1, 22,$b5,1     ; shifted B down/up
        dc.w 32,$33,0, 34,$33,$200, 36,$b3,0 ; c, repeat c, up
        dc.w 44,$4c,0, 46,$cc,0     ; bit 27: cursor up, native ANSI sequence
_timing_keys_name dc.b "LoV key fixture",0
_timing_keys_device dc.b "input.device",0
_timing_keys_intuition_name dc.b "intuition.library",0
        EVEN
_timing_keys_error dc.w 0
_timing_keys_done dc.w 0
        CNOP 0,4
_timing_keys_task dc.l 0
_timing_keys_signal dc.l 0
_timing_keys_sent dc.l 0
_timing_keys_port ds.b MP_SIZE
        EVEN
_timing_keys_io ds.b IOSTD_SIZE
        EVEN
_timing_keys_event ds.b ie_SIZEOF
        EVEN

; Bit 25 also calls the game's blocking console-read entry from main-task
; context. This is an adapter contract check, not a native dialog-route test.
_timing_keys_blocking
        movem.l d0-a6,-(sp)
        move.l (_custom5,pc),d0
        btst #25,d0
        beq .done
        move.w (_timing_study_armed,pc),d0
        beq .done
        lea (_timing_keys_blocked,pc),a0
        tst.w (a0)
        bne .done
        move.w #1,(a0)
        move.l (_hunks+4,pc),a0
        lea ($1e86,a0),a0
        jsr (a0)
        lea (_timing_keys_blocked_byte,pc),a0
        move.w d0,(a0)
        cmp.b #97,d0
        bne .bad
        lea (_timing_keys_blocked,pc),a0
        move.w #2,(a0)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_timing_keys_error,pc),a0
        move.w #2,(a0)
        bra .done
_timing_keys_blocked dc.w 0
_timing_keys_blocked_byte dc.w 0

; Bit 26 asks the normal game loop to exit after the real console events.
; The host observes collector teardown and original console close separately.
_timing_keys_exit
        movem.l d0/a0,-(sp)
        move.l (_custom5,pc),d0
        btst #26,d0
        beq .done
        move.w (_timing_keys_done,pc),d0
        beq .done
        move.l (_timing_study_watch_fields,pc),d0
        cmp.l #120,d0
        bcs .done
        move.l (_h11,pc),a0
        move.b #1,($6008,a0)
.done   movem.l (sp)+,d0/a0
        rts

        IFD TIMING_KEYS_TEXT
; Entered only by the real save/load panel. Record native elapsed time once,
; after a gameplay anchor has armed the fixture. No console byte is fabricated.
_timing_keys_text_poll
        movem.l d0/a0,-(sp)
        move.w (_timing_study_armed,pc),d0
        beq .done
        lea (_timing_keys_text_firstfield,pc),a0
        tst.l (a0)
        bne .done
        move.l (_h11,pc),a0
        move.l ($602c,a0),d0
        lea (_timing_keys_text_firstfield,pc),a0
        move.l d0,(a0)
.done   movem.l (sp)+,d0/a0
        move.l (_timing_keys_text_original,pc),-(sp)
        rts
_timing_keys_text_schedule
        dc.w 8,$20,0, 10,$a0,0       ; a
        dc.w 20,$35,1, 22,$b5,1     ; B
        dc.w 32,$33,0, 34,$33,$200, 36,$b3,0 ; c, repeat c
        dc.w 44,$41,0, 46,$c1,0     ; backspace
        dc.w 56,$44,0, 58,$c4,0     ; return, accept edited name aBc
        CNOP 0,4
_timing_keys_text_firstfield dc.l 0
_timing_keys_text_original dc.l 0
        ENDC
