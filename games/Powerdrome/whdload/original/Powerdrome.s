; Powerdrome v1.0 (Galahad/Fairlight, 22 May 2003), reconstructed.
; Labels are original code-hunk offsets. Build with -no-opt; make original compares all bytes.

	INCLUDE whdload.i
	INCLUDE whdmacros.i
_base: SLAVE_HEADER
 dc.w 15 ; ws_Version
 dc.w WHDLF_NoError|WHDLF_EmulPriv
 dc.l $80000 ; base memory
 dc.l 0
 dc.w L132-_base,0,0
 dc.b 0,$59 ; F10 exits
L020: dc.l $40000 ; Kickstart image
 dc.w _name-_base,_copy-_base,_info-_base
_name: dc.b "> POWERDROME <",0
_copy: dc.b "1989 Electronic Arts",0
_info: dc.b 10,"--------------------",10,"Installed & Fixed by",10,"Galahad of Fairlight",10,"---------------------",10,"Version 1.0 (22/05/03)",10,10,"Thanks to Slinka & Yoyo for the images",10,10,"Thanks to Frank for the installer and Icons",10,0
L111: dc.b "endcli",0
L118: dc.b "dos.library",0
L124: dc.b "Powerdrome:PD",0
L132:	bra.w L214
L136:	bsr.s L142
L138:	bset #1,$bfe001
L140:	rts
L142:	movem.l d0-a6,-(sp)
L146:	move.l d0,d7
L148:	lsl.l #2,d0
L14a:	movea.l d0,a0
L14c:	moveq #0,d0
L14e:	add.b (a0)+,d0
L150:	subq.w #1,d0
L152:	lea L111(pc),a1
L156:	cmpm.b (a0)+,(a1)+
L158:	bne.s L17a
L15a:	dbf d0,L156
L15e:	lsl.l #2,d1
L160:	movea.l d1,a0
L162:	movea.l a0,a1
L164:	cmpi.l #678035812,(a1)
L16a:	beq.s L170
L16c:	addq.l #2,a1
L16e:	bra.s L164
L170:	move.w #20217,(a1)+
L174:	lea L18c(pc),a0
L178:	move.l a0,(a1)+
L17a:	lea L1ee(pc),a0
L17e:	movea.l L60a(pc),a2
L182:	jsr 52(a2)
L186:	movem.l (sp)+,d0-a6
L18a:	rts
L18c:	movea.l ($4).w,a6
L190:	moveq #0,d0
L192:	lea L118(pc),a1
L196:	jsr -552(a6)
L19a:	movea.l d0,a6
L19c:	lea L124(pc),a0
L1a0:	move.l a0,d1
L1a2:	jsr -150(a6)
L1a6:	lsl.l #2,d0
L1a8:	tst.l d0
L1aa:	beq.s L1c8
L1ac:	movea.l d0,a0
L1ae:	movea.l d0,a1
L1b0:	cmpi.l #789466618,(a1)
L1b6:	beq.s L1bc
L1b8:	addq.l #2,a1
L1ba:	bra.s L1b0
L1bc:	move.w #20217,(a1)+
L1c0:	lea L1ca(pc),a2
L1c4:	move.l a2,(a1)+
L1c6:	jmp (a0)
L1c8:	illegal
L1ca:	move.l L1f2(pc),d2
L1ce:	beq.s L202
L1d0:	move.l #1986840924,d0
L1d6:	rts
L1d8:	rts
L1da:	dc.w $0000
L1dc:	dc.w $0000
L1de:	dc.w $0000
L1e0:	dc.w $0000
L1e2:	dc.w $0000
L1e4:	dc.w $0000
L1e6:	dc.w $0000
L1e8:	dc.w $0000
L1ea:	dc.w $0000
L1ec:	dc.w $0000
L1ee:	dc.w $8800
L1f0:	dc.w $0005
L1f2:	dc.w $0000
L1f4:	dc.w $0000
L1f6:	dc.w $8800
L1f8:	dc.w $0002
L1fa:	dc.w $0000
L1fc:	dc.w $0000
L1fe:	dc.w $0000
L200:	dc.w $0000
L202:	movea.l L60a(pc),a2
L206:	move.l #15,-(sp)
L20c:	move.l L60a(pc),-(sp)
L210:	addq.l #4,(sp)
L212:	rts
L214:	lea L60a(pc),a1
L218:	move.l a0,(a1)
L21a:	movea.l a0,a5
L21c:	lea L3ac(pc),a0
L220:	lea L5f2(pc),a1
L224:	move.l a0,(a1)
L226:	lea L5ee(pc),a0
L22a:	jsr 52(a5)
L22e:	move.l #262144,d0
L234:	move.w #-1565,d1
L238:	lea L5e2(pc),a0
L23c:	jsr 104(a5)
L240:	lea L254(pc),a0
L244:	movea.l L020(pc),a1
L248:	jsr 100(a5)
L24c:	movea.l L020(pc),a0
L250:	jmp 254(a0)
L254:	PL_START
	PL_W $132,$0000
	PL_P $61a,L326
	PL_P $592,L32a
	PL_W $25a,$0000
	PL_P $546,L332
	PL_P $1354,L338
	PL_PS $15b2,L342
	PL_PS $14b6,L35a
	PL_PS $422,L36a
	PL_I $3012
	PL_L $4f4,$ffffffff
	PL_S $4cce,$4
	PL_PS $6d70,L39e
	PL_PS $6d86,L3b6
	PL_PS $ad5e,L3d6
	PL_S $aecc,$18
	PL_P $af96,L3c0
	PL_P $b00c,L3c4
	PL_PS $d5be,L3f4
	PL_P $2a3b4,L428
	PL_I $2a5d8
	PL_P $2a0e2,L4d8
	PL_P $29cfa,L428
	PL_PS $2a6d6,L4e4
	PL_I $2af68
	PL_I $2af6e
	PL_I $2a19c
	PL_P $2960c,L516
	PL_P $4984,L418
	PL_PS $33ef0,L5ae
	PL_PS $3c9b6,L5b6
	PL_PS $36e4c,L56e
	PL_END
L326:	suba.l	a4,a4
	jmp	(a5)
L32a:	movea.l	#524288,a3
	jmp	(a5)
L332:	move.l	L5fa(pc),d0
	rts
L338:	move.w	(sp),$dff09c
	addq.l	#2,sp
	rts
L342:	subq.l	#8,sp
	move.l	8(sp),(sp)
	move.l	a3,4(sp)
	lea	L5c0(pc),a3
	move.l	a3,8(sp)
	moveq	#0,d0
	move.l	a2,d1
	rts
L35a:	move.l	(sp)+,d1
	pea	L5c0(pc)
	move.l	d1,-(sp)
	bset	#1,14(a1)
	rts
L36a:	lea	L37c(pc),a0
	move.l	a0,-28(a6)
	lea	$dff000,a0
	bra.w	L5c0
L37c:	movem.l	a0-a1,-(sp)
	movea.l	($bc).w,a0
	lea	L394(pc),a1
	move.l	a1,($bc).w
	movea.l	sp,a1
	trap	#15
	addq.l	#8,sp
	rts
L394:	move.l	a0,($bc).w
	movem.l	(a1),a0-a1
	jmp	(a5)
L39e:	lea	L60e(pc),a6
	move.l	d0,(a6)
	lea	$bfd000,a6
	rts
L3ac:	move.l	L60e(pc),$dff084
	jmp	(a0)
L3b6:	move.b	6(a0),d0
	move.b	d0,2048(a6)
	rts
L3c0:	moveq	#0,d0
	rts
L3c4:	moveq	#4,d0
	move.l	L602(pc),d1
	cmpi.l	#135168,d1
	beq.s	L3d4
	moveq	#1,d0
L3d4:	rts
L3d6:	moveq	#-2,d0
	move.l	d0,(a3)+
	move.l	a3,132(a4)
	move.l	a3,50(a2)
	move.l	a3,54(a2)
	move.l	d0,(a3)+
	clr.w	386(a4)
	addi.l	#14,(sp)
	rts
L3f4:	move.l	4(a1),d0
	beq.s	L402
	movea.l	d0,a0
	move.l	4(a0),50(a3)
L402:	move.l	8(a1),d0
	beq.s	L410
	movea.l	d0,a0
	move.l	4(a0),54(a3)
L410:	addi.l	#14,(sp)
	rts
L418:	lea	12(a3),a3
	moveq	#2,d0
	moveq	#-1,d1
L420:	move.l	d1,-(a3)
	dbf	d0,L420
	rts
L428:	moveq	#0,d1
	move.b	67(a3),d1
	clr.b	31(a1)
	btst	#1,64(a3)
	beq.s	L442
	moveq	#29,d0
	move.b	d0,31(a1)
	rts
L442:	cmpi.b	#2,29(a1)
	bne.s	L492
	movem.l	d2/a1,-(sp)
	moveq	#0,d2
	move.b	(L48c,pc,d1.w),d2
	move.l	44(a1),d0
	move.l	36(a1),d1
	movea.l	40(a1),a0
	lea	L1da(pc),a1
	move.l	a0,(a1)+
	move.l	d1,(a1)
	movea.l	L60a(pc),a1
	jsr	40(a1)
	bsr.w	L1d8
	movem.l	(sp),d2/a1
	bsr.w	L4fe
	movem.l	(sp)+,d2/a1
	moveq	#0,d0
	rts
L484:	dc.b	"Disk.",0
L48a:	dc.b	0,0
L48c:	dc.b	1,2,3,4
L490:	dc.b	15
L491:	dc.b	0
L492:	move.b	L490(pc),d0
	btst	d1,d0
	bne.s	L4a2
	moveq	#28,d0
	move.b	d0,31(a1)
	rts
L4a2:	movem.l	a1-a2,-(sp)
	lea	L484(pc),a0
	move.b	(L48c,pc,d1.w),d0
	add.b	#48,d0
	move.b	d0,5(a0)
	move.l	36(a1),d0
	move.l	44(a1),d1
	movea.l	40(a1),a1
	movea.l	L60a(pc),a2
	jsr	56(a2)
	movem.l	(sp),a1-a2
	bsr.s	L4fe
	movem.l	(sp)+,a1-a2
	moveq	#0,d0
	rts
L4d8:	moveq	#0,d0
	bchg	#7,65(a3)
	seq	d0
	rts
L4e4:	moveq	#0,d0
	move.b	67(a3),d1
	move.b	L490(pc),d0
	btst	d1,d0
	seq	d0
	move.l	d0,32(a1)
	addi.l	#44,(sp)
	rts
L4fe:	move.l	L020(pc),-(sp)
	addi.l	#171568,(sp)
	rts
L50a:	move.l	L020(pc),-(sp)
	addi.l	#169704,(sp)
	rts
L516:	bclr	#1,64(a3)
	beq.s	L524
	addq.l	#1,294(a3)
	bsr.s	L50a
L524:	move.b	67(a3),d1
	lea	L491(pc),a0
	bclr	d1,(a0)
	beq.s	L548
	bset	#1,64(a3)
	addq.l	#1,294(a3)
	bsr.s	L50a
	bclr	#1,64(a3)
	addq.l	#1,294(a3)
	bsr.s	L50a
L548:	rts
	movem.l	a6,-(sp)
	and.w	#3,d0
	lea	L491(pc),a0
	movea.l	($4).w,a6
	jsr	-120(a6)
	move.b	d1,(-5,a0,d0.w)
	bset	d0,(a0)
	jsr	-126(a6)
	movem.l	(sp)+,a6
	rts
L56e:	clr.l	12(a1)
	moveq	#12,d4
	lea	L580(pc),a6
	move.l	a4,(a6)
	lea	L58a(pc),a6
	rts
L580:	dc.w	$0000,$0000
	dc.w	$4afc
	moveq	#0,d0
	rts
L58a:	cmpa.l	L580(pc),a4
	beq.s	L594
	jmp	-12(a5)
L594:	lea	-12(a5),a6
	movem.l	d0-a6,-(sp)
	move.l	(a1),d0
	tst.l	d1
	beq.s	L5a6
	bsr.w	L136
L5a6:	movem.l	(sp)+,d0-a6
	bsr.s	L5c0
	jmp	(a6)
L5ae:	move.l	#65537,d1
	bra.s	L5c0
L5b6:	move.l	#280,d1
	bra.w	L5c0
L5c0:	move.l	L60a(pc),-(sp)
	addi.l	#32,(sp)
	rts
L5cc:	btst	#0,$dff005
	beq.s	L5cc
L5d6:	btst	#0,$dff005
	bne.s	L5d6
	rts
L5e2:	dc.b	"34005.a500",0,0	;resload_LoadKick name (devs:kickstarts/kick34005.a500)
L5ee:	dc.w	$8800,$000c
L5f2:	dc.w	$0000,$0000
	dc.w	$8800,$0000
L5fa:	dc.w	$0000,$0000
	dc.w	$8800,$0002
L602:	dc.w	$0000,$0000
	dc.w	$0000,$0000
L60a:	dc.w	$0000,$0000		;resload
L60e:	dc.w	$0000,$0000

	dc.w 0	; original hunk padding
