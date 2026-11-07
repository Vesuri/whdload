; One-degree mouse precision: release Enhanced frame rate, developer CUSTOM2 bit 7.
; Original table ownership stays with the game; only the renderer selects our
; separately owned PUBLIC table. The UI command dispatcher remains untouched.
TURN_TABLE_BYTES = 144000
_turn_install
        movem.l d0-a6,-(sp)
        move.l (_custom2,pc),d0
        btst #7,d0
        beq .done
        move.l (_custom1,pc),d0
        bne .done
        move.l (_hunks+4,pc),a0
        cmp.w #$4ef9,($2bb8,a0)
        bne .bad
        move.l (_h12,pc),a1
        lea ($229e,a1),a2
        cmp.l ($2bba,a0),a2
        bne .bad
        cmp.l #$2f2cdfca,($2740,a0)
        bne .bad
        cmp.l #$4eba0304,($2744,a0)
        bne .bad
        cmp.w #$deb9,($2904,a1)
        bne .bad
        move.l (_h11,pc),a2
        lea ($5faa,a2),a2
        cmp.l ($2906,a1),a2
        bne .bad
        move.l (_hunks+5*4,pc),a2
        cmp.l #$046c0167,($1e7e,a2)
        bne .bad
        cmp.w #$0c28,($1e82,a2)
        bne .bad
        cmp.l #$426c88d2,($1e84,a2)
        bne .bad
        cmp.l #$302c0c28,($1e88,a2)
        bne .bad
        lea (_turn_setup_original,pc),a2
        move.l ($2bba,a0),(a2)
        lea (_turn_free_resume+2,pc),a2
        lea ($2748,a0),a4
        move.l a4,(a2)
        lea (_turn_pool_free+2,pc),a2
        lea ($2a4a,a0),a4
        move.l a4,(a2)
        ; PERF_RANGE h1:02bb8 6 bit=7
        lea (_turn_setup,pc),a2
        move.l a2,($2bba,a0)
        ; PERF_RANGE h1:02740 8 bit=7
        move.w #$4ef9,($2740,a0)
        lea (_turn_free,pc),a2
        move.l a2,($2742,a0)
        move.w #$4e71,($2746,a0)
        ; PERF_RANGE h12:02904 6 bit=7
        move.w #$4eb9,($2904,a1)
        lea (_turn_table_base,pc),a2
        move.l a2,($2906,a1)
        ; Only normalize differently when a finer table is active.
        ; PERF_RANGE h5:01e7e 6 bit=7
        move.l (_hunks+5*4,pc),a2
        move.w #$4eb9,($1e7e,a2)
        lea (_turn_wrap,pc),a1
        move.l a1,($1e80,a2)
        ; PERF_RANGE h5:01e84 8 bit=7
        move.w #$4eb9,($1e84,a2)
        lea (_turn_mouse_finish,pc),a1
        move.l a1,($1e86,a2)
        move.w #$4e71,($1e8a,a2)
        IFD VERIFY
        bsr _turn_pixels_install
        ENDC
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_turn_bad,pc),a0
        bra _c2p_abort

_turn_setup
        movem.l d0-a6,-(sp)
        lea (_turn_state,pc),a5
        clr.l (4,a5)                ; unpublished until generation completes
        move.l (_h11,pc),a4
        move.w #5,($6010,a4)
        move.w ($8ca,a4),d0
        cmp.w #192,d0
        beq .supported
        cmp.w #112,d0
        beq .supported
        cmp.w #80,d0
        bne .finish
.supported
        move.l (a5),d0
        bne .allocated
        IFD VERIFY
        move.l (_custom5,pc),d0
        btst #18,d0                 ; forced PUBLIC allocation failure
        bne .finish
        ENDC
        move.l #TURN_TABLE_BYTES,d0
        moveq #MEMF_PUBLIC,d1
        move.l 4.w,a6
        jsr (_LVOAllocMem,a6)
        move.l d0,(a5)
        beq .finish
.allocated
        IFD VERIFY
        move.l (_custom5,pc),d1
        btst #22,d1
        beq .no_cycle
        lea (_turn_lifecycle_cycles,pc),a0
        tst.l (a0)
        bne .no_cycle
        bsr _turn_release
        tst.l (a5)
        bne .cycle_bad
        tst.l (4,a5)
        bne .cycle_bad
        move.l #TURN_TABLE_BYTES,d0
        moveq #MEMF_PUBLIC,d1
        move.l 4.w,a6
        jsr (_LVOAllocMem,a6)
        move.l d0,(a5)
        beq .cycle_bad
        lea (_turn_lifecycle_cycles,pc),a0
        addq.l #1,(a0)
        bra .no_cycle
.cycle_bad
        lea (_turn_bad,pc),a0
        bra _c2p_abort
.no_cycle
        ENDC
        move.l d0,a0
        move.w ($8ca,a4),d0
        move.l a4,a6
        adda.l #$8000,a6
        move.w ($c0e,a6),d1
        move.l ($5faa,a4),a1
        IFD VERIFY
        move.l ($602c,a4),d2
        ENDC
        bsr _turn_generate
        IFD VERIFY
        move.l ($602c,a4),d3
        sub.l d2,d3
        lea (_turn_generation_fields,pc),a2
        cmp.w #80,d0
        beq .generation_slot
        addq.l #4,a2
        cmp.w #112,d0
        beq .generation_slot
        addq.l #4,a2
.generation_slot
        move.l d3,(a2)
        bsr _turn_verify_table
        ENDC
        move.l (a5),(4,a5)
        move.w #1,($6010,a4)
        IFD VERIFY
        addq.l #1,(8,a5)
        move.w ($8ca,a4),(12,a5)
        ENDC
.finish movem.l (sp)+,d0-a6
        move.l (_turn_setup_original,pc),-(sp)
        rts

; Replacement ADD.L h11:05faa,D7. All other registers preserved.
_turn_table_base
        move.l a0,-(sp)
        move.l (_turn_active,pc),a0
        cmpa.w #0,a0
        bne .active
        move.l (_h11,pc),a0
        move.l ($5faa,a0),a0
.active add.l a0,d7
        move.l (sp)+,a0
        rts

_turn_wrap
        move.l d0,-(sp)
        move.l (_turn_active,pc),d0
        beq .legacy
        subi.w #360,($c28,a4)
        bra .done
.legacy subi.w #359,($c28,a4)
.done   move.l (sp)+,d0
        rts

_turn_free
        bsr _turn_release
        move.l (-8246,a4),-(sp)      ; original h1:2740 argument
        bsr _turn_pool_free
_turn_free_resume dc.w $4ef9
        dc.l 0
_turn_pool_free dc.w $4ef9
        dc.l 0

_turn_release
        movem.l d0-a6,-(sp)
        lea (_turn_state,pc),a0
        move.l (a0),a1
        clr.l (a0)
        clr.l (4,a0)
        move.l a1,d0
        beq .done
        move.l #TURN_TABLE_BYTES,d0
        move.l 4.w,a6
        jsr (_LVOFreeMem,a6)
.done   movem.l (sp)+,d0-a6
        rts

        CNOP 0,4
_turn_state
_turn_owned dc.l 0
_turn_active dc.l 0
_turn_generations dc.l 0
_turn_width dc.w 0
        EVEN
_turn_setup_original dc.l 0
_turn_bad dc.b "1 degree turning: unexpected game instructions",0
        EVEN
        INCLUDE turning_generate.s

        IFD VERIFY
        INCLUDE turning_verify.s
        ENDC

        INCLUDE turning_input.s

        IFD VERIFY
        INCLUDE turning_pixels.s
        ENDC
