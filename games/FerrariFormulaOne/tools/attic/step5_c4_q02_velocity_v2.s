writer_fixture:
 movem.l d0-d7/a0-a6,-(sp)
 lea QWriterSaved(pc),a1
 lea $68996,a0
 move.w #2,d0
.qsave0: move.w (a0)+,(a1)+
 dbra d0,.qsave0
 lea $689a6,a0
 move.w #2,d0
.qsave1: move.w (a0)+,(a1)+
 dbra d0,.qsave1
 lea $68b9e,a0
 move.w #2,d0
.qsave2: move.w (a0)+,(a1)+
 dbra d0,.qsave2
 lea $68bb2,a0
 move.w #2,d0
.qsave3: move.w (a0)+,(a1)+
 dbra d0,.qsave3
 lea $6e96e,a0
 move.w #2,d0
.qsave4: move.w (a0)+,(a1)+
 dbra d0,.qsave4
 lea $68984,a0
 move.w #2,d0
.qsave5: move.w (a0)+,(a1)+
 dbra d0,.qsave5
 lea $68b8a,a0
 move.w #2,d0
.qsave6: move.w (a0)+,(a1)+
 dbra d0,.qsave6
 lea $6f13c,a0
 move.w #15,d0
.qsave7: move.w (a0)+,(a1)+
 dbra d0,.qsave7
 lea velocity_shadow(pc),a0
 move.w #47,d0
.qsave8: move.w (a0)+,(a1)+
 dbra d0,.qsave8
 lea $2275a,a0
 move.w #7,d0
.qsave9: move.w (a0)+,(a1)+
 dbra d0,.qsave9
 lea speed_shadow(pc),a0
 move.w #23,d0
.qsave10: move.w (a0)+,(a1)+
 dbra d0,.qsave10
 lea writer_return(pc),a0
 move.w #$4ef9,$68996
 move.l a0,$68998
 move.w #$4ef9,$689a6
 move.l a0,$689a8
 move.w #$4ef9,$68b9e
 move.l a0,$68ba0
 move.w #$4ef9,$68bb2
 move.l a0,$68bb4
 move.w #$4ef9,$6e96e
 move.l a0,$6e970
 move.w #$4ef9,$68984
 move.l a0,$68986
 move.w #$4ef9,$68b8a
 move.l a0,$68b8c
 lea fake_frame+16(pc),a6
 lea writer_results(pc),a4
 moveq #0,d7
writer_case:
 bsr.w writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $6f13c,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68990
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 bsr.w writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $6f14c,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $689a0
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 bsr.w writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $6f13c,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68b98
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 bsr.w writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $6f14c,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68baa
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 bsr.w writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $6f13c,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
 move.l d5,d0
 movem.l d0-d7/a0-a6,-(sp)
 jsr $6e95e
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 bsr.w writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $2275a,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $6897e
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 bsr.w writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $2275a,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68b84
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 addq.w #1,d7
 cmpi.w #8,d7
 blo.w writer_case
writer_complete:
 lea QWriterSaved(pc),a1
 lea $68996,a0
 move.w #2,d0
.qrestore0: move.w (a1)+,(a0)+
 dbra d0,.qrestore0
 lea $689a6,a0
 move.w #2,d0
.qrestore1: move.w (a1)+,(a0)+
 dbra d0,.qrestore1
 lea $68b9e,a0
 move.w #2,d0
.qrestore2: move.w (a1)+,(a0)+
 dbra d0,.qrestore2
 lea $68bb2,a0
 move.w #2,d0
.qrestore3: move.w (a1)+,(a0)+
 dbra d0,.qrestore3
 lea $6e96e,a0
 move.w #2,d0
.qrestore4: move.w (a1)+,(a0)+
 dbra d0,.qrestore4
 lea $68984,a0
 move.w #2,d0
.qrestore5: move.w (a1)+,(a0)+
 dbra d0,.qrestore5
 lea $68b8a,a0
 move.w #2,d0
.qrestore6: move.w (a1)+,(a0)+
 dbra d0,.qrestore6
 lea $6f13c,a0
 move.w #15,d0
.qrestore7: move.w (a1)+,(a0)+
 dbra d0,.qrestore7
 lea velocity_shadow(pc),a0
 move.w #47,d0
.qrestore8: move.w (a1)+,(a0)+
 dbra d0,.qrestore8
 lea $2275a,a0
 move.w #7,d0
.qrestore9: move.w (a1)+,(a0)+
 dbra d0,.qrestore9
 lea speed_shadow(pc),a0
 move.w #23,d0
.qrestore10: move.w (a1)+,(a0)+
 dbra d0,.qrestore10
 movem.l (sp)+,d0-d7/a0-a6
 rts
writer_return:
 rts
writer_seed:
 lea speed_shadow(pc),a0
 lea $2275a,a1
 moveq #7,d0
.speedseed:
 move.l #$00641234,(a0)+
 move.w #2,(a0)+
 move.w #100,(a1)+
 dbra d0,.speedseed
 lea velocity_shadow(pc),a0
 lea $6f13c,a1
 lea $6f14c,a2
 moveq #0,d6
.loop:
 clr.w (a1)+
 move.w #200,(a2)+
 move.l d6,d0
 mulu.w #257,d0
 addi.l #256,d0
 move.l d0,(a0)+
 move.l d6,d0
 mulu.w #513,d0
 addi.l #$00c80200,d0
 move.l d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 moveq #4,d0
 sub.w d6,d0
 move.w d0,(a0)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .loop
 rts
writer_save:
 lea velocity_shadow(pc),a0
 moveq #23,d6
.shadow:
 move.l (a0)+,(a4)+
 dbra d6,.shadow
 lea $6f13c,a0
 moveq #7,d6
.arrays:
 move.l (a0)+,(a4)+
 dbra d6,.arrays
 move.l velocity_cold_writes(pc),(a4)+
 lea speed_shadow(pc),a0
 moveq #11,d6
.speedshadow:
 move.l (a0)+,(a4)+
 dbra d6,.speedshadow
 lea $2275a,a0
 moveq #3,d6
.speednative:
 move.l (a0)+,(a4)+
 dbra d6,.speednative
 rts
fake_frame: ds.b 32
writer_results: ds.b 10976
QWriterSaved: ds.b 234
