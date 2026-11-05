; Continuous 1/(5*N) s integration. Speeds keep their original units per 200 ms.
; Signed remainders prevent low speeds/turn rates being rounded to zero.
S60_SLOTS = 272
S60_REC = 144
        IFND MOVE_TRIM_SAVE
MOVE_TRIM_SAVE = 1 ; preserved-register checks and measured savings on both CPUs
        ENDC
        IFNE MOVE_TRIM_SAVE
S60_MOVE_STACK = 44
        ELSE
S60_MOVE_STACK = 60
        ENDC
        IFND RECORD_CACHE_SLOTS
RECORD_CACHE_SLOTS = 32 ; measured on both CPUs; 16 retains the baseline
        ENDC
        IFNE RECORD_CACHE_SLOTS-16
        IFNE RECORD_CACHE_SLOTS-32
        FAIL "RECORD_CACHE_SLOTS must be 16 or 32"
        ENDC
        ENDC
S60_COLLISION_FIXED SET 1
        IFD VERIFY
        IFD COLLISION_OLD
S60_COLLISION_FIXED SET 0
        ENDC
        ENDC
        IFND RECORD_CACHE_SHIFT
RECORD_CACHE_SHIFT = 4 ; measured on both CPUs; five retains the old index
        ENDC
        IFNE RECORD_CACHE_SHIFT-4
        IFNE RECORD_CACHE_SHIFT-5
        FAIL "RECORD_CACHE_SHIFT must be 4 or 5"
        ENDC
        ENDC
s60_motion_table: dc.l 0
        IFNE RECORD_CACHE
s60_record_cache: ds.l RECORD_CACHE_SLOTS ; tagged indirectly by each record's actor pointer
        ENDC
s60_move_native: ds.b 14
s60_undo_native: ds.b 14

s60_motion_install:
        cmp.l #$4eba5084,($3764,a1) ; native repeated separation caller
        bne s60_bad
        move.l a1,a0
        adda.l #$8000,a0
        cmp.l #$4e55fffc,($0682,a0)
        bne s60_bad
        cmp.l #$48e70110,($0686,a0)
        bne s60_bad
        cmp.l #$4e55fffc,($07ea,a0)
        bne s60_bad
        cmp.l #$48e70110,($07ee,a0)
        bne s60_bad
        lea (s60_move_native,pc),a3
        move.l ($0682,a0),(a3)+
        move.l ($0686,a0),(a3)+
        move.w #$4ef9,(a3)+
        lea ($068a,a0),a5
        move.l a5,(a3)
        lea (s60_undo_native,pc),a3
        move.l ($07ea,a0),(a3)+
        move.l ($07ee,a0),(a3)+
        move.w #$4ef9,(a3)+
        lea ($07f2,a0),a5
        move.l a5,(a3)
        movem.l d0-d2/a0-a1/a6,-(sp)
        move.l ($4).w,a6
        move.l #S60_SLOTS*S60_REC,d0
        move.l #$10000,d1 ; MEMF_CLEAR
        jsr (_LVOAllocMem,a6)
        lea (s60_motion_table,pc),a0
        move.l d0,(a0)
        movem.l (sp)+,d0-d2/a0-a1/a6
        move.l (s60_motion_table,pc),d0
        beq s60_bad
        bsr s60_input_guard
        move.l (s60_code,pc),a0
        adda.l #$9492,a0
        cmp.l #$48e70130,(a0)
        bne s60_bad
        cmp.l #$266f0010,(4,a0)
        bne s60_bad
        IFNE FLAT_PITCH
        move.l (s60_code,pc),a0
        adda.l #$86ae,a0
        cmp.w #$8240,(a0)
        bne s60_bad
        cmp.l #$670000b6,(2,a0)
        bne s60_bad
        move.l (s60_code,pc),a0
        adda.l #$14e88,a0
        cmp.w #$4000,(a0)
        bne s60_bad
        tst.w ($800,a0)
        bne s60_bad
        ; Flat X negates the sine as a word; exclude its sole overflow value.
        move.w #2048,d0
.trig_guard:
        cmp.w #$8000,(a0)+
        beq s60_bad
        dbf d0,.trig_guard
        ENDC
        IFNE MOVE_WORD_MUL
        ; These five calls multiply sign-extended word speed and trig values.
        ; The other two calls can receive +32768 intermediates: keep them wide.
        move.l (s60_code,pc),a0
        adda.l #$8000,a0
        cmp.l #$4eba733e,($06cc,a0)
        bne s60_bad
        cmp.l #$222f000a,($06c8,a0)
        bne s60_bad
        cmp.w #$48c0,($06c6,a0) ; EXT.L D0
        bne s60_bad
        cmp.l #$4eba72f8,($0712,a0)
        bne s60_bad
        cmp.l #$222f000c,($070e,a0)
        bne s60_bad
        cmp.w #$48c0,($070c,a0) ; EXT.L D0
        bne s60_bad
        cmp.l #$4eba72b0,($075a,a0)
        bne s60_bad
        cmp.l #$222f0008,($0756,a0)
        bne s60_bad
        cmp.w #$48c0,($0754,a0) ; EXT.L D0
        bne s60_bad
        cmp.l #$4eba7284,($0786,a0)
        bne s60_bad
        cmp.l #$222f000a,($0782,a0)
        bne s60_bad
        cmp.w #$48c0,($0780,a0) ; EXT.L D0
        bne s60_bad
        cmp.l #$4eba725e,($07ac,a0)
        bne s60_bad
        cmp.l #$222f0008,($07a8,a0)
        bne s60_bad
        cmp.w #$48c0,($07a6,a0) ; EXT.L D0
        bne s60_bad
        ENDC
        lea (s60_motion_patches,pc),a0
        jsr (resload_Patch,a2)
        rts

s60_motion_patches:
        PL_START
        IFNE FLAT_PITCH
        PL_W $86ae,$4a40 ; TST.W D0: zero pitch permits the flat path despite bank
        ENDC
        IFNE MOVE_WORD_MUL
        PL_L $86cc,$c1c14e71 ; MULS.W D1,D0 / NOP
        PL_L $8712,$c1c14e71 ; MULS.W D1,D0 / NOP
        PL_L $875a,$c1c14e71 ; MULS.W D1,D0 / NOP
        PL_L $8786,$c1c14e71 ; MULS.W D1,D0 / NOP
        PL_L $87ac,$c1c14e71 ; MULS.W D1,D0 / NOP
        ENDC
        PL_P $8682,s60_move
        PL_NOP $8688,2
        PL_P $87ea,s60_undo
        PL_NOP $87f0,2
        PL_P $9492,s60_forget
        PL_NOP $9498,2
        PL_END

s60_motion_reset:
        movem.l d0/a0,-(sp)
        move.l (s60_motion_table,pc),a0
        move.w #(S60_SLOTS*S60_REC/4)-1,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        IFNE RECORD_CACHE
        lea (s60_record_cache,pc),a0
        moveq #RECORD_CACHE_SLOTS-1,d0
.cache_clear:
        clr.l (a0)+
        dbf d0,.cache_clear
        ENDC
        movem.l (sp)+,d0/a0
        rts

; a3 = actor; return a6 = its fractional integration record. Search past
; empty entries: object removal leaves holes before still-live records.
s60_motion_record:
        IFNE RECORD_CACHE
        move.l a3,d0
        ror.l #(RECORD_CACHE_SHIFT-2),d0 ; masked LSR result, preserving X
        and.w #(RECORD_CACHE_SLOTS-1)*4,d0 ; index (actor >> RECORD_CACHE_SHIFT) masked by capacity
        IFD VERIFY
        IFD RECORD_COLLIDE
        moveq #0,d0 ; exercise every actor sharing one cache slot
        ENDC
        ENDC
        lea (s60_record_cache,pc),a0
        move.l (a0,d0.w),a6
        cmpa.w #0,a6
        beq .uncached
        cmp.l (a6),a3 ; invalidated by native removal/reset or record reuse
        beq .cached
.uncached:
        ENDC
        move.l (s60_motion_table,pc),a6
        suba.l a0,a0
        move.w #S60_SLOTS-1,d0
.find:  cmp.l (a6),a3
        beq .found
        tst.l (a6)
        bne .next
        cmpa.w #0,a0
        bne .next
        move.l a6,a0
.next:  adda.w #S60_REC,a6
        dbf d0,.find
        cmpa.w #0,a0
        beq .full
        move.l a0,a6
        move.l a3,(a6)
.found:
        IFNE RECORD_CACHE
        move.l a3,d0
        ror.l #(RECORD_CACHE_SHIFT-2),d0 ; masked LSR result, preserving X
        and.w #(RECORD_CACHE_SLOTS-1)*4,d0
        IFD VERIFY
        IFD RECORD_COLLIDE
        moveq #0,d0
        ENDC
        ENDC
        lea (s60_record_cache,pc),a0
        move.l a6,(a0,d0.w)
.cached:
        ENDC
        rts
.full:  move.l (_resload,pc),a2
        bra s60_bad

s60_forget:
        movem.l d0-d1/a0-a1,-(sp)
        move.l (20,sp),a1
        move.l (s60_motion_table,pc),a0
        move.w #S60_SLOTS-1,d0
.find:  cmp.l (a0),a1
        beq .clear
        adda.w #S60_REC,a0
        dbf d0,.find
        bra .done
.clear: moveq #(S60_REC/4)-1,d1
.zero:  clr.l (a0)+
        dbf d1,.zero
.done:  movem.l (sp)+,d0-d1/a0-a1
        movem.l d7/a2-a3,-(sp)
        move.l (16,sp),a3
        move.l (s60_code,pc),-(sp)
        add.l #$949a,(sp)
        rts

; Recognize true motion callers. Spawn placement / scripted teleport calls to
; the same native routine must retain their full displacement.
s60_is_motion:
        IFD VERIFY
        IFD LINEAR_TEST
        lea (s60_linear_return,pc),a0
        cmp.l a0,d0
        beq .yes
        ENDC
        ENDC
        IFD VERIFY
        IFD IDLE_TEST
        lea (s60_idle_return,pc),a0
        cmp.l a0,d0
        beq .yes
        ENDC
        ENDC
        IFD VERIFY
        IFD BOSS_TEST
        lea (s60_boss_test_move_return,pc),a0
        cmp.l a0,d0
        beq .yes
        ENDC
        ENDC
        lea (s60_special_charge_return,pc),a0
        cmp.l a0,d0
        beq .yes
        move.l (s60_code,pc),d1
        sub.l d1,d0
        cmp.l #$3258,d0
        beq .yes
        cmp.l #$353c,d0
        beq .yes
        cmp.l #$37f8,d0
        beq .yes
        cmp.l #$3806,d0
        beq .yes
        moveq #0,d0
        rts
.yes:   moveq #1,d0
        rts

s60_move:
        ; D5-D7/A4 are untouched by this adapter and preserved by native
        ; movement, trig and multiply callees; do not copy them redundantly.
        IFNE MOVE_TRIM_SAVE
        movem.l d0-d4/a0-a3/a5-a6,-(sp)
        ELSE
        movem.l d0-d7/a0-a6,-(sp)
        ENDC
        move.w (s60_running,pc),d0
        beq .native
        move.l (S60_MOVE_STACK,sp),d0
        bsr s60_is_motion
        tst.l d0
        beq .native
        move.l (S60_MOVE_STACK+4,sp),a3
        bsr s60_motion_record
        move.l (8,a3),(32,a6)
        move.l (12,a3),(36,a6)
        move.l (16,a3),(40,a6)
        move.l (52,a3),(44,a6)
        move.w (56,a3),(48,a6)
        move.l (8,a6),(50,a6)
        move.l (12,a6),(54,a6)
        move.l (16,a6),(58,a6)
        IFNE MOVE_IDLE
        IFD VERIFY
        IFD IDLE_TEST
        move.w (s60_idle_enable,pc),d0
        beq .integrate
        ENDC
        ENDC
        ; All snapshots above still advance, including rollback backups. With
        ; zero velocities and zero fractions the ordinary native/integration
        ; path only clears its three displacement longs. Type 7 has separate
        ; acceleration/vector bookkeeping and must always retain that path.
        tst.w ($40,a3)
        bne .integrate
        move.l (52,a3),d0
        or.l (56,a3),d0
        or.l (60,a3),d0
        bne .integrate
        move.l (8,a6),d0
        or.l (12,a6),d0
        or.l (16,a6),d0
        bne .integrate
        cmp.w #7,(2,a3)
        beq .integrate
        moveq #0,d0
        add.w d0,d0 ; ordinary zero displacement also clears the X flag
        move.l d0,(20,a6)
        move.l d0,(24,a6)
        move.l d0,(28,a6)
        bra .moved
.integrate:
        ENDC
        IFNE MOVE_LINEAR
        IFD VERIFY
        IFD LINEAR_TEST
        move.w (s60_linear_enable,pc),d0
        beq .ordinary_rotations
        ENDC
        ENDC
        bsr s60_linear_move
        tst.l d0
        beq .ordinary_rotations
        ; Ordinary final Y integration has a zero remainder/displacement here.
        moveq #0,d0
        add.w d0,d0
        bra .moved
.ordinary_rotations:
        ENDC
        lea (52,a3),a0
        lea (8,a6),a1
        moveq #2,d2
.rot:   move.w (a0),d0
        ext.l d0
        move.w (a1),d1
        ext.l d1
        add.l d1,d0
        S60_DIV12 d0
        move.w d0,(a0)+
        swap d0
        move.w d0,(a1)+
        dbf d2,.rot
        bsr s60_boss_speed_enter
        IFNE MOVE_ZERO
        tst.w ($40,a3)
        bne .native_move
        bsr s60_move_zero
        bra .after_native
.native_move:
        ENDC
        move.l a3,-(sp)
        bsr s60_move_native
        addq.l #4,sp
.after_native:
        cmp.w #7,(2,a3)
        bne .ordinary
        bsr s60_boss_move_finish
        bra .moved
.ordinary:
        move.l (44,a6),(52,a3)
        move.w (48,a6),(56,a3)
        lea (8,a3),a0
        lea (14,a6),a1
        lea (32,a6),a5
        lea (20,a6),a3
        moveq #2,d2
.pos:   move.l (a0),d0
        sub.l (a5),d0
        move.w (a1),d1
        ext.l d1
        add.l d1,d0
        IFEQ S60_SUBSTEPS-1
        move.l d0,d1 ; native displacement can exceed a signed word
        swap d0
        clr.w d0
        swap d0 ; packed remainder must remain zero
        ELSE
        S60_DIV12 d0
        move.w d0,d1
        ext.l d1
        ENDC
        move.l d1,(a3)+ ; exact displacement, for collision rollback
        add.l (a5)+,d1
        move.l d1,(a0)+
        swap d0
        move.w d0,(a1)+
        dbf d2,.pos
.moved:
        IFNE MOVE_TRIM_SAVE
        movem.l (sp)+,d0-d4/a0-a3/a5-a6
        ELSE
        movem.l (sp)+,d0-d7/a0-a6
        ENDC
        rts
.native:
        IFNE MOVE_TRIM_SAVE
        movem.l (sp)+,d0-d4/a0-a3/a5-a6
        ELSE
        movem.l (sp)+,d0-d7/a0-a6
        ENDC
        bra s60_move_native

        IFNE MOVE_ZERO
; Called only by the all-register-saving integration wrapper with forward
; speed zero. Native $868e..$86a2 rotations and $87c4..$87de linear terms
; still apply. Every skipped trigonometric product has a zero speed operand.
; This is not a native-entry replacement: its scratch-register results differ.
s60_move_zero:
        move.w (52,a3),d0
        add.w d0,(20,a3)
        move.w (54,a3),d0
        add.w d0,(22,a3)
        move.w (56,a3),d0
        add.w d0,(24,a3)
        move.w (58,a3),d0
        ext.l d0
        add.l d0,(8,a3)
        move.w (60,a3),d0
        ext.l d0
        add.l d0,(12,a3)
        move.w (62,a3),d0
        ext.l d0
        add.l d0,(16,a3)
        rts
        ENDC

s60_undo:
        movem.l d0-d7/a0-a6,-(sp)
        IFD VERIFY
        IFD COLLISION_TEST
        bsr s60_collision_probe
        ENDC
        ENDC
        move.w (s60_running,pc),d0
        beq .native
        move.l (64,sp),a3
        bsr s60_motion_record
        IFNE S60_COLLISION_FIXED
        move.l (60,sp),d0
        sub.l (s60_code,pc),d0
        cmp.l #$3768,d0
        bne .rollback
        ; The player collision loop has already doubled speed (or supplied 10
        ; when stopped). This is spatial separation, not undo of a timed step.
        ; Preserve native correction strides so zero substep motion cannot
        ; trap that loop, and retain the reference bounce response.
        move.w (56,a6),(14,a6)
        move.l (58,a6),(16,a6)
        bra .native
.rollback:
        ENDC
        move.l (20,a6),d0
        sub.l d0,(8,a3)
        move.l (24,a6),d0
        sub.l d0,(12,a3)
        move.l (122,a6),(116,a6)
        move.w (126,a6),(120,a6)
        move.l (28,a6),d0
        sub.l d0,(16,a3)
        move.w (56,a6),(14,a6)
        move.l (58,a6),(16,a6)
        movem.l (sp)+,d0-d7/a0-a6
        rts
.native:
        movem.l (sp)+,d0-d7/a0-a6
        bra s60_undo_native

; The input routine uses MOVEQ immediates for acceleration and braking.
; Change only those immediates before each input sample. Directly assigned
; velocities and maximum speeds retain their native units. Flush after changing code: the
; loader enables the instruction cache on CPUs that support it.
; Entries: hunk offset, original instruction, quantum-table row offset.
S60_INPUT_NEUTRAL_FIXED SET 1
        IFD VERIFY
        IFD INPUT_NEUTRAL_OLD
S60_INPUT_NEUTRAL_FIXED SET 0 ; diagnostic reproduces unscaled neutral braking
        ENDC
        ENDC
        IFND INPUT_QUANTA_UNROLL
INPUT_QUANTA_UNROLL = 1 ; native-byte twins, cross-render checks and measured savings
        ENDC
; One site list emits either the guard/restore table or the per-tick stores.
S60_INPUT_SITE MACRO
        IFEQ S60_INPUT_EMIT_STORES
        dc.l \1
        dc.w \2,\3
        ELSE
        IFEQ \3
        move.b d0,(\1-$10000+1,a0)
        ELSE
        IFEQ \3-S60_SUBSTEPS
        move.b d1,(\1-$10000+1,a0)
        ELSE
        move.b d2,(\1-$10000+1,a0)
        ENDC
        ENDC
        ENDC
        ENDM
S60_INPUT_ENTRIES MACRO
        S60_INPUT_SITE $fea8,$7050,0
        S60_INPUT_SITE $feb6,$7050,0
        S60_INPUT_SITE $fed0,$7050,0
        S60_INPUT_SITE $fede,$7050,0
        S60_INPUT_SITE $ff02,$7050,0
        S60_INPUT_SITE $ff1e,$7450,0
        S60_INPUT_SITE $ff26,$7450,0
        S60_INPUT_SITE $ffa2,$700a,S60_SUBSTEPS
        S60_INPUT_SITE $ffb0,$700a,S60_SUBSTEPS
        S60_INPUT_SITE $1000e,$720a,S60_SUBSTEPS
        S60_INPUT_SITE $1002a,$760a,S60_SUBSTEPS
        S60_INPUT_SITE $10032,$720a,S60_SUBSTEPS
        IFNE S60_INPUT_NEUTRAL_FIXED
        ; No direction and disabled analogue fallback take this separate turn
        ; braking path. It uses the same 80-units-per-native-step schedule.
        S60_INPUT_SITE $1004e,$7050,0
        S60_INPUT_SITE $1006a,$7450,0
        S60_INPUT_SITE $10072,$7050,0
        ENDC
        S60_INPUT_SITE $10080,$7028,2*S60_SUBSTEPS
        ENDM
S60_INPUT_EMIT_STORES SET 0
s60_input_sites:
        S60_INPUT_ENTRIES
        dc.l 0
; floor((phase+1)*increment/N) - floor(phase*increment/N).
; Exactly 80, 10 and 40 native velocity units over each N-tick interval.
s60_input_values:
S60_QUANTA_ROW MACRO
s60_quanta_index SET 0
        REPT S60_SUBSTEPS
        dc.b ((s60_quanta_index+1)*\1)/S60_SUBSTEPS-(s60_quanta_index*\1)/S60_SUBSTEPS
s60_quanta_index SET s60_quanta_index+1
        ENDR
        ENDM
        S60_QUANTA_ROW 80
        S60_QUANTA_ROW 10
        S60_QUANTA_ROW 40
        EVEN
s60_input_guard:
        movem.l d0-d1/a0/a3,-(sp)
        lea (s60_input_sites,pc),a0
.next:  move.l (a0)+,d0
        beq .done
        move.l a1,a3
        adda.l d0,a3
        move.w (a0)+,d1
        cmp.w (a3),d1
        bne s60_bad
        addq.l #2,a0
        bra .next
.done:  movem.l (sp)+,d0-d1/a0/a3
        rts

s60_input_quanta:
        IFNE INPUT_QUANTA_UNROLL
        movem.l d0-d2/a0-a2,-(sp)
        move.l (s60_code,pc),a0
        adda.l #$10000,a0
        lea (s60_input_values,pc),a1
        move.w (s60_phase,pc),d0
        adda.w d0,a1
        move.b (a1),d0
        move.b (S60_SUBSTEPS,a1),d1
        move.b (2*S60_SUBSTEPS,a1),d2
S60_INPUT_EMIT_STORES SET 1
        S60_INPUT_ENTRIES
S60_INPUT_EMIT_STORES SET 0
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d2/a0-a2
        rts
        ELSE
        movem.l d0-d3/a0-a3,-(sp)
        move.l (s60_code,pc),a0
        lea (s60_input_sites,pc),a1
        lea (s60_input_values,pc),a2
        move.w (s60_phase,pc),d0
        adda.w d0,a2
.next:  move.l (a1)+,d1
        beq .done
        addq.l #2,a1
        move.w (a1)+,d2
        move.b (a2,d2.w),d3
        move.l a0,a3
        adda.l d1,a3
        move.b d3,(1,a3)
        bra .next
.done:  move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d3/a0-a3
        rts

        ENDC

; Menus and scripted sequences outside the fixed-step loop use native units.
s60_input_restore:
        movem.l d0-d1/a0-a2,-(sp)
        lea (s60_input_sites,pc),a0
.next:  move.l (a0)+,d0
        beq .done
        move.l (s60_code,pc),a1
        adda.l d0,a1
        move.w (a0)+,(a1)
        addq.l #2,a0
        bra .next
.done:  move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
