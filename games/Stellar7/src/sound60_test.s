; SOUND_TWIN (VERIFY): compare the 68000 channel pass with native $134c on every
; timer call. A RAM copy of native $134c..$13db, its two Paula constants
; retargeted to a shadow block, runs twice from the same channel records, with
; the block filled with two different sentinels; a register word is written
; exactly when both runs leave the same value. The replacement runs the same
; way into its own shadow block. Channel records (all 336 bytes) and written
; Paula words must match, then the replacement runs for real and must again
; produce the native records. Calls that would enter a native note-start or
; another class's method are run normally and counted as skipped.
; SOUND_TWIN_BAD perturbs the replacement's volume (negative control).

S60_TEST_SOUND_BLOCK = 10+4*16 ; DMACON word, then AUD0..AUD3 at +10
S60_TEST_SOUND_STATE = 4*S60_SOUND_RECORD
s60_test_sound_record:
        dc.b 'ST60'
s60_test_sound_calls: dc.l 0
s60_test_sound_compared: dc.l 0
s60_test_sound_skipped: dc.l 0
s60_test_sound_state_errors: dc.l 0
s60_test_sound_write_errors: dc.l 0
s60_test_sound_real_errors: dc.l 0
s60_test_sound_reference_errors: dc.l 0
s60_test_sound_written: dc.l 0 ; written Paula words in compared calls
s60_test_sound_first: dc.l 0 ; call number, kind (1 state, 2 write, 3 real, 4 reference)
s60_test_sound_first_kind: dc.w 0
s60_test_sound_first_index: dc.w 0
s60_test_sound_first_native: dc.w 0
s60_test_sound_first_replacement: dc.w 0
        EVEN
s60_test_sound_native: ds.b $13dc-$134c
s60_test_sound_pre: ds.b S60_TEST_SOUND_STATE
s60_test_sound_reference: ds.b S60_TEST_SOUND_STATE
s60_test_sound_n: ds.b S60_TEST_SOUND_BLOCK
s60_test_sound_n1: ds.b S60_TEST_SOUND_BLOCK
s60_test_sound_n2: ds.b S60_TEST_SOUND_BLOCK
s60_test_sound_o: ds.b S60_TEST_SOUND_BLOCK
s60_test_sound_o1: ds.b S60_TEST_SOUND_BLOCK
s60_test_sound_o2: ds.b S60_TEST_SOUND_BLOCK
        EVEN

; Before the patch list is applied: copy native $134c and retarget it.
s60_test_sound_install:
        movem.l d0-d1/a0-a1,-(sp)
        move.l (s60_code,pc),a0
        adda.l #$134c,a0
        lea (s60_test_sound_native,pc),a1
        move.w #($13dc-$134c)/2-1,d0
.copy:  move.w (a0)+,(a1)+
        dbf d0,.copy
        lea (s60_test_sound_native,pc),a1
        lea (s60_test_sound_n+10,pc),a0
        move.l a0,($13a6-$134c,a1) ; LEA $dff0a0,a2
        subq.l #8,a0
        subq.l #2,a0
        move.l a0,($13d6-$134c,a1) ; MOVE.W d6,$dff096
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a1
        rts

; A0 = destination, D0.W = sentinel word.
s60_test_sound_fill:
        moveq #S60_TEST_SOUND_BLOCK/2-1,d1
.fill:  move.w d0,(a0)+
        dbf d1,.fill
        rts
; A0 = source, A1 = destination, D1 = byte count/2-1.
s60_test_sound_copy:
.copy:  move.w (a0)+,(a1)+
        dbf d1,.copy
        rts
s60_test_sound_save:
        lea (522,a6),a0
        move.w #S60_TEST_SOUND_STATE/2-1,d1
        bra s60_test_sound_copy
s60_test_sound_restore:
        lea (s60_test_sound_pre,pc),a0
        lea (522,a6),a1
        move.w #S60_TEST_SOUND_STATE/2-1,d1
        bra s60_test_sound_copy
; Compare the live records with the native reference. D2 = error kind.
; Returns Z set when equal; records the first difference.
s60_test_sound_check:
        lea (522,a6),a0
        lea (s60_test_sound_reference,pc),a1
        moveq #0,d1
.cmp:   move.w (a0)+,d0
        cmp.w (a1)+,d0
        bne .differ
        addq.w #2,d1
        cmp.w #S60_TEST_SOUND_STATE,d1
        bne .cmp
        rts
.differ:
        move.w (-2,a1),d3
        exg d0,d3 ; D0 native, D3 replacement
        bsr s60_test_sound_first_error
        moveq #1,d0 ; Z clear
        rts
; D2 = kind, D1 = index, D0 = native word, D3 = replacement word.
s60_test_sound_first_error:
        move.l a0,-(sp)
        lea (s60_test_sound_first,pc),a0
        tst.w (s60_test_sound_first_kind-s60_test_sound_first,a0)
        bne .done
        move.l (s60_test_sound_calls,pc),(a0)+
        move.w d2,(a0)+
        move.w d1,(a0)+
        move.w d0,(a0)+
        move.w d3,(a0)
.done:  move.l (sp)+,a0
        rts
s60_test_sound_count:
        addq.l #1,(a0)
        rts

s60_test_sound_channels:
        lea (s60_test_sound_calls,pc),a0
        addq.l #1,(a0)
        ; Native note starts and other classes are not shadowed.
        lea (522,a6),a1
        move.l (s60_sound_class,pc),a3
        moveq #3,d7
.scan:  move.b (a1),d0
        or.b (1,a1),d0
        beq .scan_next
        move.l (4,a1),d0
        beq .scan_next
        move.l d0,a4
        cmpa.l (a4),a3
        bne .skip
        cmp.b #1,(a1)
        beq .skip
.scan_next:
        lea (S60_SOUND_RECORD,a1),a1
        dbf d7,.scan
        lea (s60_test_sound_pre,pc),a1
        bsr s60_test_sound_save
        ; Native reference, twice.
        lea (s60_test_sound_n,pc),a0
        move.w #$5555,d0
        bsr s60_test_sound_fill
        jsr (s60_test_sound_native,pc)
        lea (s60_test_sound_n,pc),a0
        lea (s60_test_sound_n1,pc),a1
        moveq #S60_TEST_SOUND_BLOCK/2-1,d1
        bsr s60_test_sound_copy
        lea (s60_test_sound_reference,pc),a1
        bsr s60_test_sound_save
        bsr s60_test_sound_restore
        lea (s60_test_sound_n,pc),a0
        move.w #$aaaa,d0
        bsr s60_test_sound_fill
        jsr (s60_test_sound_native,pc)
        lea (s60_test_sound_n,pc),a0
        lea (s60_test_sound_n2,pc),a1
        moveq #S60_TEST_SOUND_BLOCK/2-1,d1
        bsr s60_test_sound_copy
        moveq #4,d2
        bsr s60_test_sound_check
        beq .replacement
        lea (s60_test_sound_reference_errors,pc),a0
        bsr s60_test_sound_count
.replacement:
        bsr s60_test_sound_restore
        lea (s60_test_sound_o,pc),a0
        move.w #$5555,d0
        bsr s60_test_sound_fill
        lea (s60_test_sound_o+10,pc),a0
        move.l a0,d5
        bsr s60_sound_core
        lea (s60_test_sound_o,pc),a0
        lea (s60_test_sound_o1,pc),a1
        moveq #S60_TEST_SOUND_BLOCK/2-1,d1
        bsr s60_test_sound_copy
        moveq #1,d2
        bsr s60_test_sound_check
        beq .second
        lea (s60_test_sound_state_errors,pc),a0
        bsr s60_test_sound_count
.second:
        bsr s60_test_sound_restore
        lea (s60_test_sound_o,pc),a0
        move.w #$aaaa,d0
        bsr s60_test_sound_fill
        lea (s60_test_sound_o+10,pc),a0
        move.l a0,d5
        bsr s60_sound_core
        lea (s60_test_sound_o,pc),a0
        lea (s60_test_sound_o2,pc),a1
        moveq #S60_TEST_SOUND_BLOCK/2-1,d1
        bsr s60_test_sound_copy
        ; Written words: equal in both sentinel runs. Compare set and values.
        lea (s60_test_sound_n1,pc),a0
        lea (s60_test_sound_n2,pc),a1
        lea (s60_test_sound_o1,pc),a2
        lea (s60_test_sound_o2,pc),a3
        moveq #0,d1
        moveq #0,d4 ; errors in this call
.word:  move.w (a0)+,d0
        move.w (a2)+,d3
        cmp.w (a1)+,d0
        seq d6 ; native wrote
        cmp.w (a3)+,d3
        seq d7 ; replacement wrote
        cmp.b d6,d7
        bne .write_error
        tst.b d6
        beq .word_next
        lea (s60_test_sound_written,pc),a4
        addq.l #1,(a4)
        cmp.w d0,d3
        beq .word_next
.write_error:
        moveq #2,d2
        bsr s60_test_sound_first_error
        moveq #1,d4
.word_next:
        addq.w #2,d1
        cmp.w #S60_TEST_SOUND_BLOCK,d1
        bne .word
        tst.w d4
        beq .real
        lea (s60_test_sound_write_errors,pc),a0
        bsr s60_test_sound_count
.real:  bsr s60_test_sound_restore
        bsr s60_sound_channels
        moveq #3,d2
        bsr s60_test_sound_check
        beq .compared
        lea (s60_test_sound_real_errors,pc),a0
        bsr s60_test_sound_count
.compared:
        lea (s60_test_sound_compared,pc),a0
        addq.l #1,(a0)
        rts
.skip:  lea (s60_test_sound_skipped,pc),a0
        addq.l #1,(a0)
        bra s60_sound_channels
