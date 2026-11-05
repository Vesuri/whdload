writer_fixture:
 movem.l d0-d7/a0-a6,-(sp)
 lea QWriterSaved(pc),a1
 lea $663fa,a0
 move.w #2,d0
.qsave0: move.w (a0)+,(a1)+
 dbra d0,.qsave0
 lea $68c18,a0
 move.w #2,d0
.qsave1: move.w (a0)+,(a1)+
 dbra d0,.qsave1
 lea $6895e,a0
 move.w #2,d0
.qsave2: move.w (a0)+,(a1)+
 dbra d0,.qsave2
 lea $688e8,a0
 move.w #2,d0
.qsave3: move.w (a0)+,(a1)+
 dbra d0,.qsave3
 lea $68920,a0
 move.w #2,d0
.qsave4: move.w (a0)+,(a1)+
 dbra d0,.qsave4
 lea $68ac0,a0
 move.w #2,d0
.qsave5: move.w (a0)+,(a1)+
 dbra d0,.qsave5
 lea $68b2c,a0
 move.w #2,d0
.qsave6: move.w (a0)+,(a1)+
 dbra d0,.qsave6
 lea $6a61a,a0
 move.w #15,d0
.qsave7: move.w (a0)+,(a1)+
 dbra d0,.qsave7
 lea $227ca,a0
 move.w #7,d0
.qsave8: move.w (a0)+,(a1)+
 dbra d0,.qsave8
 lea position_shadow(pc),a0
 move.w #47,d0
.qsave9: move.w (a0)+,(a1)+
 dbra d0,.qsave9
 lea saved_position(pc),a0
 move.w #23,d0
.qsave10: move.w (a0)+,(a1)+
 dbra d0,.qsave10
 lea writer_return(pc),a0
 move.w #$4ef9,$663fa
 move.l a0,$663fc
 move.w #$4ef9,$68c18
 move.l a0,$68c1a
 move.w #$4ef9,$6895e
 move.l a0,$68960
 move.w #$4ef9,$688e8
 move.l a0,$688ea
 move.w #$4ef9,$68920
 move.l a0,$68922
 move.w #$4ef9,$68ac0
 move.l a0,$68ac2
 move.w #$4ef9,$68b2c
 move.l a0,$68b2e
 lea fake_frame+16(pc),a6
 lea writer_results(pc),a4
 moveq #0,d7
writer_case:
 lea position_shadow(pc),a0
 lea saved_position(pc),a1
 moveq #0,d6
writer_seed:
 move.w d6,d0
 mulu.w #12,d0
 move.l d6,d1
 add.l d1,d1
 lea $6a61a,a2
 move.w #10,(a2,d1.w)
 lea $6a62a,a2
 move.w #100,(a2,d1.w)
 lea $227ca,a2
 move.w #50,(a2,d1.w)
 move.w #10,(a0)+
 move.w d6,d0
 mulu.w #257,d0
 addi.w #256,d0
 move.w d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 move.w #100,(a0)+
 move.w d6,d0
 mulu.w #513,d0
 addi.w #512,d0
 move.w d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 move.w #50,(a1)+
 move.l #$12340002,(a1)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $227ca,a0
 adda.l d5,a0
 lea $6a62a,a1
 adda.l d5,a1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $663f4
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 ; Change the current coordinate and tail after snapshot, before restore.
 move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+6(pc),a0
 adda.l d0,a0
 move.w #200,(a0)
 move.l #$beef0003,2(a0)
 lea $6a62a,a0
 adda.l d5,a0
 move.w #200,(a0)
 lea $227ca,a1
 adda.l d5,a1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68c12
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+0(pc),a0
 adda.l d0,a0
 move.l #$f00dfffd,2(a0)
 lea $6a61a,a0
 adda.l d5,a0
 move.w #111,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $6886e
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+6(pc),a0
 adda.l d0,a0
 move.l #$f00dfffd,2(a0)
 lea $6a62a,a0
 adda.l d5,a0
 move.w #222,d0
 movem.l d0-d7/a0-a6,-(sp)
 jsr $688e2
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+0(pc),a0
 adda.l d0,a0
 move.l #$f00dfffd,2(a0)
 lea $6a61a,a0
 adda.l d5,a0
 move.w #333,d0
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68918
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+0(pc),a0
 adda.l d0,a0
 move.l #$f00dfffd,2(a0)
 lea $6a61a,a0
 adda.l d5,a0
 move.w #444,d0
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68ab8
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+6(pc),a0
 adda.l d0,a0
 move.l #$f00dfffd,2(a0)
 lea $6a62a,a0
 adda.l d5,a0
 move.w #0,d0
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68b26
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 addq.w #1,d7
 cmpi.w #8,d7
 blo.w writer_case
writer_complete:
 lea QWriterSaved(pc),a1
 lea $663fa,a0
 move.w #2,d0
.qrestore0: move.w (a1)+,(a0)+
 dbra d0,.qrestore0
 lea $68c18,a0
 move.w #2,d0
.qrestore1: move.w (a1)+,(a0)+
 dbra d0,.qrestore1
 lea $6895e,a0
 move.w #2,d0
.qrestore2: move.w (a1)+,(a0)+
 dbra d0,.qrestore2
 lea $688e8,a0
 move.w #2,d0
.qrestore3: move.w (a1)+,(a0)+
 dbra d0,.qrestore3
 lea $68920,a0
 move.w #2,d0
.qrestore4: move.w (a1)+,(a0)+
 dbra d0,.qrestore4
 lea $68ac0,a0
 move.w #2,d0
.qrestore5: move.w (a1)+,(a0)+
 dbra d0,.qrestore5
 lea $68b2c,a0
 move.w #2,d0
.qrestore6: move.w (a1)+,(a0)+
 dbra d0,.qrestore6
 lea $6a61a,a0
 move.w #15,d0
.qrestore7: move.w (a1)+,(a0)+
 dbra d0,.qrestore7
 lea $227ca,a0
 move.w #7,d0
.qrestore8: move.w (a1)+,(a0)+
 dbra d0,.qrestore8
 lea position_shadow(pc),a0
 move.w #47,d0
.qrestore9: move.w (a1)+,(a0)+
 dbra d0,.qrestore9
 lea saved_position(pc),a0
 move.w #23,d0
.qrestore10: move.w (a1)+,(a0)+
 dbra d0,.qrestore10
 movem.l (sp)+,d0-d7/a0-a6
 rts
writer_return:
 rts
writer_save:
 lea position_shadow(pc),a0
 moveq #23,d6
.shadow:
 move.l (a0)+,(a4)+
 dbra d6,.shadow
 lea saved_position(pc),a0
 moveq #11,d6
.saved:
 move.l (a0)+,(a4)+
 dbra d6,.saved
 lea $6a61a,a0
 moveq #7,d6
.arrays:
 move.l (a0)+,(a4)+
 dbra d6,.arrays
 lea $227ca,a0
 moveq #3,d6
.native_saved:
 move.l (a0)+,(a4)+
 dbra d6,.native_saved
 rts
fake_frame: ds.b 32
writer_results: ds.b 10752
QWriterSaved: ds.b 234
