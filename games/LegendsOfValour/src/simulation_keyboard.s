; Task-context console collector. Own the game's one outstanding CMD_READ;
; never call console.device from VBL. Main gameplay polls historical bytes,
; while blocking/dialog readers consume the same FIFO without a tick cutoff.
        INCLUDE "exec/tasks.i"
        IFD VERIFY
        IFND SIM_KEYS_SLOTS
SIM_KEYS_SLOTS = 512
        ENDC
        ELSE
SIM_KEYS_SLOTS = 512
        ENDC
SIM_KEYS_RING = (TC_SIZE+3)&$fffffffc
SIM_KEYS_STACK = SIM_KEYS_RING+SIM_KEYS_SLOTS*8
SIM_KEYS_BYTES = SIM_KEYS_STACK+4096

_sim_keys_check
        move.l (_hunks+4,pc),a2
        lea (.specs,pc),a0
        moveq #3,d2
.next   move.w (a0)+,d0
        cmp.l #$bfecde40,(0,a2,d0.w)
        bne .bad
        addq.w #4,d0
        move.l (a0)+,d1
        cmp.l (0,a2,d0.w),d1
        bne .bad
        dbf d2,.next
        rts
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort
.specs  dc.w $1e56
        dc.l $65000b0a
        dc.w $1e86
        dc.l $65000ada
        dc.w $1eb6
        dc.l $65000aaa
        dc.w $1f30
        dc.l $65000a30

_sim_keys_install
        move.l (_hunks+4,pc),a2
        lea (_sim_keys_overflow_target,pc),a0
        lea ($2966,a2),a1
        move.l a1,(a0)+
        lea ($1f38,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h1:01e56 8 bit=6
        lea ($1e56,a2),a0
        lea (_sim_keys_start,pc),a1
        bsr .jump
        ; PERF_RANGE h1:01e86 8 bit=6
        lea ($1e86,a2),a0
        lea (_sim_keys_wait,pc),a1
        bsr .jump
        ; PERF_RANGE h1:01eb6 8 bit=6
        lea ($1eb6,a2),a0
        lea (_sim_keys_poll,pc),a1
        bsr .jump
        ; PERF_RANGE h1:01f30 8 bit=6
        lea ($1f30,a2),a0
        lea (_sim_keys_stop,pc),a1
.jump   move.w #$4ef9,(a0)+
        move.l a1,(a0)+
        move.w #$4e71,(a0)
        rts

_sim_keys_stack_overflow
        move.l (_sim_keys_overflow_target,pc),-(sp)
        rts

_sim_keys_start
        cmpa.l ($5e40-32768,a4),sp
        bcs _sim_keys_stack_overflow
        movem.l d0-d3/a0-a3/a6,-(sp)
        move.l 4.w,a6
        move.l #SIM_KEYS_BYTES,d0
        move.l #MEMF_PUBLIC+MEMF_CLEAR,d1
        jsr (_LVOAllocMem,a6)
        tst.l d0
        beq _sim_keys_bad
        lea (_sim_keys_task,pc),a0
        move.l d0,(a0)
        move.l d0,a2
        move.l (_h11,pc),a0
        move.l ($5f60,a0),a1
        lea (_sim_keys_port,pc),a3
        move.l a1,(a3)
        move.l MP_SIGTASK(a1),(_sim_keys_owner-_sim_keys_port,a3)
        moveq #0,d1
        move.b MP_SIGBIT(a1),d1
        moveq #1,d0
        lsl.l d1,d0
        move.l d0,(_sim_keys_signal-_sim_keys_port,a3)
        move.l a2,MP_SIGTASK(a1)
        move.l ($5f5c,a0),(_sim_keys_request-_sim_keys_port,a3)
        lea (_sim_keys_head,pc),a0
        clr.l (a0)                      ; head and tail words
        clr.w (_sim_keys_stopping-_sim_keys_head,a0)
        clr.w (_sim_keys_error-_sim_keys_head,a0)
        clr.w (_sim_keys_pending-_sim_keys_head,a0)
        clr.w (_sim_keys_full-_sim_keys_head,a0)
        move.w #1,(_sim_keys_live-_sim_keys_head,a0)
        move.b #NT_TASK,LN_TYPE(a2)
        move.b #5,LN_PRI(a2)
        lea (_sim_keys_name,pc),a0
        move.l a0,LN_NAME(a2)
        lea SIM_KEYS_STACK(a2),a0
        move.l a0,TC_SPLOWER(a2)
        adda.l #4096,a0
        move.l a0,TC_SPUPPER(a2)
        move.l a0,TC_SPREG(a2)
        lea TC_MEMENTRY(a2),a0
        lea LH_TAIL(a0),a1
        move.l a1,LH_HEAD(a0)
        move.l a0,LH_TAILPRED(a0)
        move.l a2,a1
        lea (_sim_keys_worker,pc),a2
        suba.l a3,a3
        jsr (_LVOAddTask,a6)
        movem.l (sp)+,d0-d3/a0-a3/a6
        rts

_sim_keys_worker
        move.l 4.w,a6
        move.l (_sim_keys_port,pc),a0
        moveq #0,d0
        move.b MP_SIGBIT(a0),d0
        jsr (_LVOAllocSignal,a6)
        tst.l d0
        bmi .error
.submit
        move.l (_sim_keys_request,pc),a1
        move.w #2,28(a1)                ; CMD_READ
        move.l #1,36(a1)
        move.l (_h11,pc),a0
        lea ($5fa4,a0),a0
        move.l a0,40(a1)
        lea (_sim_keys_pending,pc),a0
        move.w #1,(a0)
        jsr (_LVOSendIO,a6)
.receive
        move.w (_sim_keys_stopping,pc),d0
        bne .stop
        move.l (_sim_keys_port,pc),a0
        jsr (_LVOGetMsg,a6)
        tst.l d0
        beq .wait
        lea (_sim_keys_pending,pc),a0
        clr.w (a0)
        move.l (_sim_keys_request,pc),a1
        tst.b 31(a1)                    ; io_Error
        bne .error
        cmp.l #1,32(a1)                 ; io_Actual
        bne .error
        moveq #0,d5                ; world clock domain
        move.l (_sim_fields,pc),d4
        IFD SIM_COMBAT_EXPERIMENT
        move.w (_sim_combat_active,pc),d0
        beq .timestamp
        moveq #1,d5                ; combat uses elapsed VBL fields
        move.l (_h11,pc),a0
        move.l ($602c,a0),d4
.timestamp
        ENDC
        addq.l #1,d4                    ; retain arrival even if the queue is full
.enqueue
        move.w (_sim_keys_stopping,pc),d0
        bne .stop
        moveq #0,d1
        move.w (_sim_keys_head,pc),d1
        move.w d1,d2
        addq.w #1,d2
        and.w #SIM_KEYS_SLOTS-1,d2
        cmp.w (_sim_keys_tail,pc),d2
        beq .full
        lea (_sim_keys_full,pc),a0
        clr.w (a0)
        lsl.w #3,d1
        move.l (_sim_keys_task,pc),a0
        lea SIM_KEYS_RING(a0),a0
        adda.w d1,a0
        move.l d4,(a0)
        move.l (_h11,pc),a1
        move.b ($5fa4,a1),4(a0)
        move.b d5,5(a0)
        lea (_sim_keys_head,pc),a0
        move.w d2,(a0)                  ; publish only after complete record
        bsr .signal_owner
        bra .submit
; No new CMD_READ until this completed byte has been published. The owner
; signals when it removes an entry. The worker runs above owner priority, so
; setting full and waiting cannot lose an intervening owner notification.
.full   lea (_sim_keys_full,pc),a0
        move.w #1,(a0)
        IFD VERIFY
        lea (_sim_keys_full_waits,pc),a0
        addq.l #1,(a0)
        ENDC
        move.l (_sim_keys_signal,pc),d0
        jsr (_LVOWait,a6)
        bra .enqueue
.wait   move.l (_sim_keys_signal,pc),d0
        jsr (_LVOWait,a6)
        bra .receive
.error  lea (_sim_keys_error,pc),a0
        move.w #1,(a0)
        bsr .signal_owner
.error_wait
        move.l (_sim_keys_signal,pc),d0
        jsr (_LVOWait,a6)
        move.w (_sim_keys_stopping,pc),d0
        beq .error_wait
        ; Error is fatal to the consumer; no normal shutdown is expected here.
.stop   move.w (_sim_keys_pending,pc),d0
        beq .restored
        move.l (_sim_keys_request,pc),a1
        jsr (_LVOAbortIO,a6)
        move.l (_sim_keys_request,pc),a1
        jsr (_LVOWaitIO,a6)
.restored
        lea (_sim_keys_pending,pc),a0
        clr.w (a0)
        clr.w (_sim_keys_full-_sim_keys_pending,a0)
        move.l (_sim_keys_port,pc),a0
        move.l (_sim_keys_owner,pc),MP_SIGTASK(a0)
        jsr (_LVOForbid,a6)
        lea (_sim_keys_live,pc),a0
        clr.w (a0)
        bsr .signal_owner
        suba.l a1,a1
        jmp (_LVORemTask,a6)            ; cannot resume owner before self-removal
.signal_owner
        move.l (_sim_keys_owner,pc),a1
        move.l (_sim_keys_signal,pc),d0
        jmp (_LVOSignal,a6)

_sim_keys_poll
        cmpa.l ($5e40-32768,a4),sp
        bcs _sim_keys_stack_overflow
        movem.l d1-d3/a0-a2/a6,-(sp)
        moveq #0,d3
        IFD SIM_COMBAT_EXPERIMENT
        move.l (_hunks+9*4,pc),a0
        lea ($5ac,a0),a1
        cmp.l (28,sp),a1
        bne .world
        moveq #2,d3                ; end-of-combat-step cutoff
        bra .read
.world
        ENDC
        move.l (_hunks+4,pc),a0
        lea ($258e,a0),a1
        cmp.l (28,sp),a1
        beq .historical
        lea ($25b2,a0),a1
        cmp.l (28,sp),a1
        bne .read
.historical
        move.w (_sim_started,pc),d0
        beq .read
        move.w (_sim_suspended,pc),d0
        bne .read
        moveq #1,d3
.read   bsr _sim_keys_take
        movem.l (sp)+,d1-d3/a0-a2/a6
        rts

_sim_keys_wait
        cmpa.l ($5e40-32768,a4),sp
        bcs _sim_keys_stack_overflow
        movem.l d1-d3/a0-a2/a6,-(sp)
        move.l 4.w,a6
        moveq #0,d3
.again  bsr _sim_keys_take
        tst.l d1                       ; distinguish empty from a zero byte
        bne .done
        IFD VERIFY
        lea (_sim_keys_waits,pc),a0
        addq.l #1,(a0)
        ENDC
        move.l (_sim_keys_signal,pc),d0
        jsr (_LVOWait,a6)
        bra .again
.done   movem.l (sp)+,d1-d3/a0-a2/a6
        rts

; D3!=0 applies the gameplay cutoff. D0=byte/zero, D1=present flag.
_sim_keys_take
        move.w (_sim_keys_error,pc),d0
        bne _sim_keys_bad
        moveq #0,d0
        moveq #0,d1
        moveq #0,d2
        move.w (_sim_keys_tail,pc),d2
        cmp.w (_sim_keys_head,pc),d2
        beq .done
        move.l (_sim_keys_task,pc),a0
        lea SIM_KEYS_RING(a0),a0
        lsl.w #3,d2
        adda.w d2,a0
        tst.w d3
        beq .consume
        IFD SIM_COMBAT_EXPERIMENT
        cmp.w #2,d3
        beq .combat_cutoff
        tst.b (5,a0)
        bne .consume              ; pending bytes from the previous mode
        ENDC
        move.l (_sim_consumed,pc),d2
        bra .cutoff
        IFD SIM_COMBAT_EXPERIMENT
.combat_cutoff
        tst.b (5,a0)
        beq .consume              ; queued before combat began
        move.l (_sim_combat_deadline,pc),d2
        ENDC
.cutoff sub.l (a0),d2
        bmi .done
.consume
        move.b 4(a0),d0
        IFD VERIFY
        lea (_sim_keys_reads,pc),a1
        move.l (a1),d2
        cmp.l #64,d2
        bcc .logged
        addq.l #1,(a1)
        mulu.w #12,d2
        lea (_sim_keys_reads,pc),a1
        adda.l #_sim_keys_readlog-_sim_keys_reads,a1
        adda.w d2,a1
        move.l (a0),(a1)
        move.l (_sim_consumed,pc),(4,a1)
        IFD SIM_COMBAT_EXPERIMENT
        cmp.w #2,d3
        bne .logged_clock
        move.l (_sim_combat_deadline,pc),(4,a1)
.logged_clock
        ENDC
        move.w d0,(8,a1)
        move.w d3,(10,a1)
.logged
        ENDC
        lea (_sim_keys_tail,pc),a0
        addq.w #1,(a0)
        and.w #SIM_KEYS_SLOTS-1,(a0)
        move.w (_sim_keys_full,pc),d1
        beq .present
        movem.l d0/a6,-(sp)
        move.l 4.w,a6
        move.l (_sim_keys_task,pc),a1
        move.l (_sim_keys_signal,pc),d0
        jsr (_LVOSignal,a6)
        movem.l (sp)+,d0/a6
.present
        moveq #1,d1
.done   rts

_sim_keys_stop
        cmpa.l ($5e40-32768,a4),sp
        bcs _sim_keys_stack_overflow
        movem.l d0-d2/a0-a2/a6,-(sp)
        move.l 4.w,a6
        lea (_sim_keys_stopping,pc),a0
        move.w #1,(a0)
        move.l (_sim_keys_task,pc),a1
        move.l (_sim_keys_signal,pc),d0
        jsr (_LVOSignal,a6)
.wait   move.w (_sim_keys_live,pc),d0
        beq .free
        move.l (_sim_keys_signal,pc),d0
        jsr (_LVOWait,a6)
        bra .wait
.free   move.l (_sim_keys_task,pc),a1
        move.l #SIM_KEYS_BYTES,d0
        jsr (_LVOFreeMem,a6)
        lea (_sim_keys_task,pc),a0
        clr.l (a0)
        movem.l (sp)+,d0-d2/a0-a2/a6
        IFD VERIFY
_sim_keys_stopped
        nop
        ENDC
        move.l (_sim_keys_close_continue,pc),-(sp)
        rts

_sim_keys_bad
        lea (_sim_keys_bad_message,pc),a0
        bra _c2p_abort
_sim_keys_name dc.b "LoV keyboard",0
_sim_keys_bad_message dc.b "Simulation: keyboard collector failed",0
        EVEN
_sim_keys_head dc.w 0
_sim_keys_tail dc.w 0
_sim_keys_stopping dc.w 0
_sim_keys_error dc.w 0
_sim_keys_live dc.w 0
_sim_keys_pending dc.w 0
_sim_keys_full dc.w 0
        CNOP 0,4
_sim_keys_task dc.l 0
_sim_keys_port dc.l 0
_sim_keys_owner dc.l 0
_sim_keys_signal dc.l 0
_sim_keys_request dc.l 0
_sim_keys_overflow_target dc.l 0
_sim_keys_close_continue dc.l 0

        IFD VERIFY
        CNOP 0,4
_sim_keys_full_waits dc.l 0
_sim_keys_waits dc.l 0
_sim_keys_reads dc.l 0
        ENDC
