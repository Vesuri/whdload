; Diagnostic frame-part recorder, assembled only with --frame-stats.
; Record: event id (bits 31-27), field relative to the first recorded field
; (bits 26-9) and beam line (bits 8-0). The field is the game's VBL count.
; Recording starts FS_SKIP active fields after the first active event, fills
; the buffer once, and the next loop entry saves it with resload_SaveFile.
; Header: 'WCFS', field Hz, record count, skipped fields.
        ifne BUFFERED
FS_RECORDS = 8192
        else
FS_RECORDS = 16384
        endif
FS_SKIP = 150

frame_stats_init:
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l  #16+FS_RECORDS*4,d0
        ifne BUFFERED
        addi.l  #16+2047*16,d0
        endif
        move.l  #$10005,d1       ; MEMF_CLEAR | MEMF_FAST | MEMF_PUBLIC
        move.l  $4.w,a6
        jsr     -198(a6)
        lea     frame_stats_buffer(pc),a0
        move.l  d0,(a0)
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts

; Stack: return address, then the event id word pushed by FSTAT.
; Preserves every register and the condition codes.
frame_stat:
        movem.l d0-d3/a0,-(sp)
        move.w  ccr,-(sp)
        tst.w   timing_active(pc)
        beq.w   .done
        move.l  frame_stats_buffer(pc),d0
        beq.w   .done
        move.l  frame_stats_count(pc),d1
        cmpi.l  #FS_RECORDS,d1
        bhs.s   .done
        move.l  timing_data(pc),a0
.sample:
        ; A field change between the two counter reads retries the sample.
        move.l  $7f02(a0),d2
        move.l  $dff004,d0
        move.l  $dff004,d3
        cmp.l   $7f02(a0),d2
        bne.s   .sample
        lsr.l   #8,d0
        andi.l  #$1ff,d0
        lsr.l   #8,d3
        andi.l  #$1ff,d3
        ; VPOSR/VHPOSR are two bus reads, not one atomic longword.
        ; Require agreeing beam lines to reject a torn 255/256 transition.
        cmp.l   d3,d0
        bne.s   .sample
        tst.w   frame_stats_started(pc)
        bne.s   .started
        lea     frame_stats_started(pc),a0
        move.w  #1,(a0)
        addi.l  #FS_SKIP,d2
        lea     frame_stats_first(pc),a0
        move.l  d2,(a0)
        bra.s   .done
.started:
        sub.l   frame_stats_first(pc),d2
        bmi.s   .done
        andi.l  #$3ffff,d2
        lsl.l   #8,d2
        add.l   d2,d2
        or.l    d2,d0
        moveq   #0,d2
        move.w  26(sp),d2
        ror.l   #5,d2
        or.l    d2,d0
        move.l  frame_stats_buffer(pc),a0
        move.l  d0,16(a0,d1.l*4)
        addq.l  #1,d1
        lea     frame_stats_count(pc),a0
        move.l  d1,(a0)
.done:
        move.w  (sp)+,ccr
        movem.l (sp)+,d0-d3/a0
        rts

frame_stats_flush:
        movem.l d0-d1/a0-a2,-(sp)
        move.w  ccr,-(sp)
        move.l  frame_stats_count(pc),d0
        cmpi.l  #FS_RECORDS,d0
        blo.s   .done
        tst.w   frame_stats_saved(pc)
        bne.s   .done
        lea     frame_stats_saved(pc),a0
        move.w  #1,(a0)
        move.l  frame_stats_buffer(pc),a1
        ifne BUFFERED
        bsr.w   frame_stats_save_display
        move.l  frame_stats_buffer(pc),a1
        endif
        move.l  #'WCFS',(a1)
        move.l  timing_hz(pc),4(a1)
        move.l  #FS_RECORDS,8(a1)
        move.l  #FS_SKIP,12(a1)
        lea     frame_stats_name(pc),a0
        move.l  #16+FS_RECORDS*4,d0
        move.l  slave+$121e(pc),a2
        jsr     12(a2)           ; resload_SaveFile
.done:
        move.w  (sp)+,ccr
        movem.l (sp)+,d0-d1/a0-a2
        rts

        cnop    0,4
frame_stats_buffer:  dc.l 0
frame_stats_count:   dc.l 0
frame_stats_first:   dc.l 0
frame_stats_started: dc.w 0
frame_stats_saved:   dc.w 0
frame_stats_name:    dc.b 'framestats.bin',0
        cnop    0,4

        ifne BUFFERED
; A separate IRQ-owned ledger avoids making the main-thread recorder reentrant.
; Header: WCDS, Hz, count, entry size. Entry: field.l, line.w, index.w,
; planar.l, copper.l. Main thread saves only the completed prefix.
frame_stats_display:
        tst.w   frame_stats_started(pc)
        beq.w   .done
        cmpi.l  #FS_RECORDS,frame_stats_count(pc)
        bhs.w   .done
        move.l  timing_data(pc),a0
        move.l  $7f02(a0),d2
        sub.l   frame_stats_first(pc),d2
        bmi.s   .done
        move.l  frame_stats_display_count(pc),d1
        cmpi.l  #2047,d1
        bhs.s   .done
        move.l  frame_stats_buffer(pc),a0
        adda.l  #16+FS_RECORDS*4+16,a0
        lsl.l   #4,d1
        adda.l  d1,a0
        move.l  d2,(a0)+
        move.w  d0,(a0)+
        move.w  release_pending_index(pc),(a0)+
        move.l  release_pending_plane(pc),(a0)+
        move.l  -778(a4),a1
        move.l  50(a1),(a0)+
        lea     frame_stats_display_count(pc),a0
        addq.l  #1,(a0)
.done:
        rts
frame_stats_save_display:
        move.l  frame_stats_buffer(pc),a1
        adda.l  #16+FS_RECORDS*4,a1
        move.l  #'WCDS',(a1)
        move.l  timing_hz(pc),4(a1)
        move.l  frame_stats_display_count(pc),d0
        move.l  d0,8(a1)
        move.l  #16,12(a1)
        lsl.l   #4,d0
        addi.l  #16,d0
        lea     frame_stats_display_name(pc),a0
        move.l  slave+$121e(pc),a2
        jsr     12(a2)           ; separate completed display ledger
        rts
        cnop 0,4
frame_stats_display_count: dc.l 0
frame_stats_display_name: dc.b 'displaystats.bin',0
        cnop 0,4
        endif
