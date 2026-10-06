; Battlehawks 1942 WHDLoad slave v1.0 (Galahad of Fairlight, 12/05/03), reconstructed.
;
; No source was distributed. This file is a disassembly of the shipped
; Battlehawks1942.Slave (1512 bytes, the "SLOW" slave of the Retroplay pack
; Battlehawks1942_v1.0_0053.lha) that vasm rebuilds byte-identically:
;   make -C whdload original      (assembles and compares with the installed slave)
; Labels Lxxx are the shipped slave's hunk offsets. Kept as the reference for what v1.0 does;
; the slave that is built and patched is ../Battlehawks1942.s (WHDLoad 20 KickEmu).
;
; What it does (an old-style Kickstart 1.3 slave, before kickemu):
;  - resload_LoadKick loads kick34005.A500 into ws_ExpMem ($40000 bytes = only the ROM, so the
;    emulated machine is the 512 KB of BaseMem: the game, its data and the OS all live in chip RAM);
;  - L206 is a resload_Patch list for the Kickstart image (offsets from its start, i.e. ROM
;    address - $FC0000): trackdisk reads go to Disk.1-3 through resload_DiskLoad (L3da), disk
;    changes, the copper pointer, and a dos.library LoadSeg hook (L520/L53c);
;  - the LoadSeg hook (L126) runs once: when the loaded file is "BH" it replaces the manual
;    protection check, the first `move.b (0,a0,d1.l),d2; cmp.w d2,d0; beq` (BH hunk 0 offset
;    $025be), with `jsr L17c; bra.s`.
; The game boots from Disk.1's own startup-sequence ("BH") on the emulated Kickstart 1.3.
;



	INCLUDE	whdload.i
	INCLUDE	whdmacros.i

_base:	SLAVE_HEADER
	dc.w	15			;ws_Version
	dc.w	WHDLF_NoError|WHDLF_EmulPriv	;ws_Flags
	dc.l	$80000			;ws_BaseMemSize
	dc.l	0			;ws_ExecInstall
	dc.w	L116-_base		;ws_GameLoader
	dc.w	0			;ws_CurrentDir
	dc.w	0			;ws_DontCache
	dc.b	0			;ws_keydebug
	dc.b	$59			;ws_keyexit = F10
L020:	dc.l	$40000			;ws_ExpMem (the Kickstart image goes here)
	dc.w	_name-_base		;ws_name
	dc.w	_copy-_base		;ws_copy
	dc.w	_info-_base		;ws_info

_name:	dc.b	"> Battlehawks 1942 <",0
_copy:	dc.b	"1990 Lucasfilm Games",0
_info:	dc.b	10,"--------------------",10,"Installed & Fixed by",10,"Galahad of Fairlight",10,"---------------------",10,"Version 1.0 (12/05/03)",10,10,"Thanks to Mad Matt for the images",10,10,"Thanks to Frank for the installer and Icons",10,0
L112:	dc.b	"BH",0,0		;name of the file the LoadSeg hook patches
L116:	bra.w	L1c6
L11a:	bsr.s	L126
	bset	#1,$bfe001
	rts
L126:	movem.l	d0-a6,-(sp)		;LoadSeg hook: d0 = BSTR name, d1 = seglist (BPTRs)
	move.l	d0,d7
	lsl.l	#2,d0
	movea.l	d0,a0
	moveq	#0,d0
	add.b	(a0)+,d0
	subq.w	#1,d0
	lea	L112(pc),a1
L13a:	cmpm.b	(a0)+,(a1)+
	bne.s	L162
	dbf	d0,L13a
	lsl.l	#2,d1
	movea.l	d1,a0
	movea.l	a0,a1
L148:	cmpi.l	#$14301800,(a1)		;move.b (0,a0,d1.l),d2: the manual check
	beq.s	L154
	addq.l	#2,a1
	bra.s	L148
L154:	move.w	#$4eb9,(a1)+		;jsr L17c
	lea	L17c(pc),a0
	move.l	a0,(a1)+
	move.w	#$6078,(a1)+		;bra.s past the check
L162:	lea	L1a0(pc),a0		;resload_Control (flush caches)
	movea.l	L5bc(pc),a2
	jsr	52(a2)
	lea	L126(pc),a0
	move.w	L188(pc),(a0)		;rts: run only once
	movem.l	(sp)+,d0-a6
	rts
L17c:	move.l	L1a4(pc),d2
	beq.s	L1b4
	move.b	d0,(0,a0,d1.l)
	move.l	d0,d2
L188:	rts
L18a:	rts
L18c:	dc.w	$0000,$0000
L190:	dc.w	$0000,$0000
	dc.w	$0000,$0000
	dc.w	$0000,$0000
	dc.w	$0000,$0000
L1a0:	dc.w	$8800,$0005
L1a4:	dc.w	$0000,$0000
	dc.w	$8800,$0002
	dc.w	$0000,$0000
	dc.w	$0000,$0000
L1b4:	movea.l	L5bc(pc),a2
	move.l	#15,-(sp)
	move.l	L5bc(pc),-(sp)
	addq.l	#4,(sp)
	rts
L1c6:	lea	L5bc(pc),a1		;GameLoader: a0 = resload
	move.l	a0,(a1)
	movea.l	a0,a5
	lea	L35e(pc),a0
	lea	L5a4(pc),a1
	move.l	a0,(a1)
	lea	L5a0(pc),a0
	jsr	52(a5)
	move.l	#$40000,d0		;resload_LoadKick kick34005.A500
	move.w	#-1565,d1
	lea	L594(pc),a0
	jsr	104(a5)
	lea	L206(pc),a0
	movea.l	L020(pc),a1
	jsr	100(a5)
	movea.l	L020(pc),a0
	jmp	254(a0)			;boot the Kickstart (ROM entry $FC00D2)
L206:					;Kickstart patch list
	PL_START
	PL_W	$132,$0000
	PL_P	$61a,L2d8
	PL_P	$592,L2dc
	PL_W	$25a,$0000
	PL_P	$546,L2e4
	PL_P	$1354,L2ea
	PL_PS	$15b2,L2f4
	PL_PS	$14b6,L30c
	PL_PS	$422,L31c
	PL_I	$3012
	PL_L	$4f4,$ffffffff
	PL_S	$4cce,$4
	PL_PS	$6d70,L350
	PL_PS	$6d86,L368
	PL_PS	$ad5e,L388
	PL_S	$aecc,$18
	PL_P	$af96,L372
	PL_P	$b00c,L376
	PL_PS	$d5be,L3a6
	PL_P	$2a3b4,L3da
	PL_I	$2a5d8
	PL_P	$2a0e2,L48a
	PL_P	$29cfa,L3da
	PL_PS	$2a6d6,L496
	PL_I	$2af68
	PL_I	$2af6e
	PL_I	$2a19c
	PL_P	$2960c,L4c8
	PL_P	$4984,L3ca
	PL_PS	$33ef0,L560
	PL_PS	$3c9b6,L568
	PL_PS	$36e4c,L520
	PL_END
L2d8:	suba.l	a4,a4
	jmp	(a5)
L2dc:	movea.l	#524288,a3
	jmp	(a5)
L2e4:	move.l	L5ac(pc),d0
	rts
L2ea:	move.w	(sp),$dff09c
	addq.l	#2,sp
	rts
L2f4:	subq.l	#8,sp
	move.l	8(sp),(sp)
	move.l	a3,4(sp)
	lea	L572(pc),a3
	move.l	a3,8(sp)
	moveq	#0,d0
	move.l	a2,d1
	rts
L30c:	move.l	(sp)+,d1
	pea	L572(pc)
	move.l	d1,-(sp)
	bset	#1,14(a1)
	rts
L31c:	lea	L32e(pc),a0
	move.l	a0,-28(a6)
	lea	$dff000,a0
	bra.w	L572
L32e:	movem.l	a0-a1,-(sp)
	movea.l	($bc).w,a0
	lea	L346(pc),a1
	move.l	a1,($bc).w
	movea.l	sp,a1
	trap	#15
	addq.l	#8,sp
	rts
L346:	move.l	a0,($bc).w
	movem.l	(a1),a0-a1
	jmp	(a5)
L350:	lea	L5c0(pc),a6
	move.l	d0,(a6)
	lea	$bfd000,a6
	rts
L35e:	move.l	L5c0(pc),$dff084
	jmp	(a0)
L368:	move.b	6(a0),d0
	move.b	d0,2048(a6)
	rts
L372:	moveq	#0,d0
	rts
L376:	moveq	#4,d0
	move.l	L5b4(pc),d1
	cmpi.l	#135168,d1
	beq.s	L386
	moveq	#1,d0
L386:	rts
L388:	moveq	#-2,d0
	move.l	d0,(a3)+
	move.l	a3,132(a4)
	move.l	a3,50(a2)
	move.l	a3,54(a2)
	move.l	d0,(a3)+
	clr.w	386(a4)
	addi.l	#14,(sp)
	rts
L3a6:	move.l	4(a1),d0
	beq.s	L3b4
	movea.l	d0,a0
	move.l	4(a0),50(a3)
L3b4:	move.l	8(a1),d0
	beq.s	L3c2
	movea.l	d0,a0
	move.l	4(a0),54(a3)
L3c2:	addi.l	#14,(sp)
	rts
L3ca:	lea	12(a3),a3
	moveq	#0,d0
	moveq	#-1,d1
L3d2:	move.l	d1,-(a3)
	dbf	d0,L3d2
	rts
L3da:	moveq	#0,d1
	move.b	67(a3),d1
	clr.b	31(a1)
	btst	#1,64(a3)
	beq.s	L3f4
	moveq	#29,d0
	move.b	d0,31(a1)
	rts
L3f4:	cmpi.b	#2,29(a1)
	bne.s	L444
	movem.l	d2/a1,-(sp)
	moveq	#0,d2
	move.b	(L43e,pc,d1.w),d2
	move.l	44(a1),d0
	move.l	36(a1),d1
	movea.l	40(a1),a0
	lea	L18c(pc),a1
	move.l	a0,(a1)+
	move.l	d1,(a1)
	movea.l	L5bc(pc),a1
	jsr	40(a1)
	bsr.w	L18a
	movem.l	(sp),d2/a1
	bsr.w	L4b0
	movem.l	(sp)+,d2/a1
	moveq	#0,d0
	rts
L436:	dc.b	"Disk.",0
L43c:	dc.b	0,0
L43e:	dc.b	1,2,3,4
L442:	dc.b	15
L443:	dc.b	0
L444:	move.b	L442(pc),d0
	btst	d1,d0
	bne.s	L454
	moveq	#28,d0
	move.b	d0,31(a1)
	rts
L454:	movem.l	a1-a2,-(sp)
	lea	L436(pc),a0
	move.b	(L43e,pc,d1.w),d0
	add.b	#48,d0
	move.b	d0,5(a0)
	move.l	36(a1),d0
	move.l	44(a1),d1
	movea.l	40(a1),a1
	movea.l	L5bc(pc),a2
	jsr	56(a2)
	movem.l	(sp),a1-a2
	bsr.s	L4b0
	movem.l	(sp)+,a1-a2
	moveq	#0,d0
	rts
L48a:	moveq	#0,d0
	bchg	#7,65(a3)
	seq	d0
	rts
L496:	moveq	#0,d0
	move.b	67(a3),d1
	move.b	L442(pc),d0
	btst	d1,d0
	seq	d0
	move.l	d0,32(a1)
	addi.l	#44,(sp)
	rts
L4b0:	move.l	L020(pc),-(sp)
	addi.l	#171568,(sp)
	rts
L4bc:	move.l	L020(pc),-(sp)
	addi.l	#169704,(sp)
	rts
L4c8:	bclr	#1,64(a3)
	beq.s	L4d6
	addq.l	#1,294(a3)
	bsr.s	L4bc
L4d6:	move.b	67(a3),d1
	lea	L443(pc),a0
	bclr	d1,(a0)
	beq.s	L4fa
	bset	#1,64(a3)
	addq.l	#1,294(a3)
	bsr.s	L4bc
	bclr	#1,64(a3)
	addq.l	#1,294(a3)
	bsr.s	L4bc
L4fa:	rts
	movem.l	a6,-(sp)
	and.w	#3,d0
	lea	L443(pc),a0
	movea.l	($4).w,a6
	jsr	-120(a6)
	move.b	d1,(-5,a0,d0.w)
	bset	d0,(a0)
	jsr	-126(a6)
	movem.l	(sp)+,a6
	rts
L520:	clr.l	12(a1)
	moveq	#12,d4
	lea	L532(pc),a6
	move.l	a4,(a6)
	lea	L53c(pc),a6
	rts
L532:	dc.w	$0000,$0000
	dc.w	$4afc
	moveq	#0,d0
	rts
L53c:	cmpa.l	L532(pc),a4
	beq.s	L546
	jmp	-12(a5)
L546:	lea	-12(a5),a6
	movem.l	d0-a6,-(sp)
	move.l	(a1),d0
	tst.l	d1
	beq.s	L558
	bsr.w	L11a
L558:	movem.l	(sp)+,d0-a6
	bsr.s	L572
	jmp	(a6)
L560:	move.l	#65537,d1
	bra.s	L572
L568:	move.l	#280,d1
	bra.w	L572
L572:	move.l	L5bc(pc),-(sp)
	addi.l	#32,(sp)
	rts
L57e:	btst	#0,$dff005
	beq.s	L57e
L588:	btst	#0,$dff005
	bne.s	L588
	rts
L594:	dc.b	"34005.a500",0,0	;resload_LoadKick name (devs:kickstarts/kick34005.a500)
L5a0:	dc.w	$8800,$000c
L5a4:	dc.w	$0000,$0000
	dc.w	$8800,$0000
L5ac:	dc.w	$0000,$0000
	dc.w	$8800,$0002
L5b4:	dc.w	$0000,$0000
	dc.w	$0000,$0000
L5bc:	dc.w	$0000,$0000		;resload
L5c0:	dc.w	$0000,$0000

