;*---------------------------------------------------------------------------
;  :Program.	mercenary3.slave.asm
;  :Contents.	Slave for "Mercenary 3 - The Dion Crisis"
;  :Author.	Harry/Graham/Wepl
;  :History.	19.03.1998
;		29.07.04 merged Harry and Graham (ReSourced Slave) sources
;		performance version, from whdload/original/ (the shipped 1.2):
;		WHDLoad 17 header with options; with every option off the game
;		runs as with the shipped slave
;  :Requires.	whdload-package :)
;  :Copyright.	Freeware
;  :Language.	68000 Assembler
;  :Translator.	vasm
;  :To Do.
;---------------------------------------------------------------------------*

	INCLUDE	whdload.i
	INCLUDE	whdmacros.i

STACKSIZE	= $1000

;======================================================================

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	17			;ws_Version
		dc.w	WHDLF_NoError|WHDLF_Disk|WHDLF_EmulTrap	;ws_flags
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	_boot-_base		;ws_GameLoader
		dc.w	0			;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$41			;ws_keyexit = Backspace
_expmem		dc.l	STACKSIZE		;ws_ExpMem (Custom1 bit 2's stack)
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info
		dc.w	0			;ws_kickname
		dc.l	0			;ws_kicksize
		dc.w	0			;ws_kickcrc
		dc.w	_config-_base		;ws_config

;============================================================================

_name		dc.b	"Mercenary 3 - The Dion Crisis",0
_copy		dc.b	"1991 Novagen",0
_info		dc.b	"adapted by Harry/Graham/Wepl",10
		dc.b	"Version 1.2 (29.07.2004)",10
		dc.b	"performance version in development"
	IFD VERIFY
		dc.b	" (VERIFY)"
	ENDC
		dc.b	0
_config		dc.b	"C1:X:Enable display DMA once, copy whole palette:0;"
		dc.b	"C1:X:64-bit bitplane fetch on AGA (FMODE 3):1;"
		dc.b	"C1:X:Supervisor stack in expansion memory:2;"
		dc.b	0
Mercenary3sav	dc.b	'Mercenary3.save',0,0
	EVEN

;======================================================================
_boot		;	A0 = resident loader
;======================================================================

	lea	($1800).w,sp
	move.l	sp,usp
	lea	(_resload,pc),a1
	move.l	a0,(a1)
	movea.l	a0,a2
	lea	(_tags,pc),a0
	jsr	(resload_Control,a2)

	lea	($4000).w,a0
	moveq	#0,d0
	move.l	#$7D80,d1
	bsr.w	_diskload

	lea	(_int68,pc),a0
	move.l	a0,($68).w
	move.b	#$7F,(_ciaa+ciaicr).l
	tst.b	(_ciaa+ciaicr).l
	move.w	#(INTF_PORTS|INTF_INTEN|INTF_SETCLR),(_custom+intena).l
	move.b	#(CIAICRF_SP|CIAICRF_SETCLR),(_ciaa+ciaicr).l

	lea	($4080).w,a0
	lea	($48000).l,a1
	move.w	#$F9F,d0
lbC00010C	move.w	(a0)+,(a1)+
	move.w	(a0)+,($1FFE,a1)
	move.w	(a0)+,($3FFE,a1)
	move.w	(a0)+,($5FFE,a1)
	dbra	d0,lbC00010C
	moveq	#15,d0
	lea	($4004).w,a0
	lea	(_custom+color).l,a1
lbC00012A	move.w	(a0)+,d1
	add.w	d1,d1
	move.w	d1,(a1)+
	dbra	d0,lbC00012A
	lea	(_custom).l,a6
	lea	(_clist,pc),a0
	lea	($800).w,a1
	move.l	a1,(cop1lc,a6)
lbC000146	move.l	(a0)+,(a1)+
	bpl.b	lbC000146
	clr.w	(copjmp1,a6)
	bsr.w	_waitvb
	move.w	#(DMAF_COPPER|DMAF_RASTER|DMAF_MASTER|DMAF_SETCLR),(dmacon,a6)

	moveq	#50,d0
	jsr	(resload_Delay,a2)

	bsr.w	_waitvb
	move.w	#$7FFF,(dmacon,a6)

	lea	($100).w,a0
	move.w	#$FFDF,d0
lbC00018C	clr.l	(a0)+
	clr.l	(a0)+
	dbra	d0,lbC00018C

	lea	($5350).w,a0
	move.l	#$9000,d0
	move.l	#$6D7B0,d1
	bsr.w	_diskload

	lea	($56300).l,a1
	lea	(8).w,a0
	move.l	a0,($32,a1)
	addq.l	#1,a0
	move.l	a0,($2A,a1)
	move.l	a0,($3E,a1)
	move.l	a0,($4C,a1)

	move.w	(_attn,pc),d0
	btst	#AFB_68040,d0
	beq.b	lbC0002AA
	lea	($C0).w,a0
	move.l	a0,($458CC).l
	addq.l	#4,a0
	move.l	a0,($458D6).l
	addq.l	#4,a0
	move.l	a0,($4F87C).l
	addq.l	#4,a0
	move.l	a0,($4F882).l
	move.l	#$207800C0,d0
	move.w	#$4E90,d1
	move.l	d0,($459B8).l
	move.w	d1,($459BC).l
	addq.w	#4,d0
	move.l	d0,($459C4).l
	move.w	d1,($459C8).l
	addq.w	#4,d0
	move.l	d0,($4F9C0).l
	move.w	d1,($4F9C4).l
	addq.w	#4,d0
	move.l	d0,($4FA08).l
	move.w	d1,($4FA0C).l
lbC0002AA

	lea	$5a1b0,a0
	cmpi.w	#$4eb9,(a0)		;copy protected version?
	bne.b	.notprotected
	move.w	#$7000,d0
	move.w	d0,(a0)+
	move.w	d0,(a0)+
	move.w	d0,(a0)+
.notprotected

	lea	(_pl,pc),a0
	lea	$50000,a1
	jsr	(resload_Patch,a2)

	moveq	#CACRF_EnableI,d0
	move.l	d0,d1
	movea.l	(_resload,pc),a0
	jsr	(resload_SetCACR,a0)

; Custom1 bit 1: on AGA (Lisa's ID in LISAID), fetch the bitplanes 64 bits wide. The
; game's two in-game copper lists (Disk.1 $56780, $567CC) are the only ones that set the
; fetch window; their 320-pixel window ends at $b8 with 64-bit fetches. The buffers and
; planes are 8-byte aligned and the rows 40 bytes, without modulos.
	btst	#1,(_custom1+3,pc)
	beq.b	.nofmode
	move.w	(_custom+$7c).l,d0	;LISAID
	cmp.b	#$f8,d0
	bne.b	.nofmode
	move.w	#$b8,($52aee).l		;DDFSTOP
	move.w	#$b8,($52b32).l
	move.w	#3,(_custom+$1fc).l	;FMODE
.nofmode
; Custom1 bit 2: the game sets its supervisor stack at the top of chip RAM with
; lea $7fffa,a0 / unlk a0 in three places (Disk.1 $5DE66, $5DE88, $5DEEA) and uses less
; than a page of it. Move it into the expansion memory, which is fast RAM when fitted.
	btst	#2,(_custom1+3,pc)
	beq.b	.nostack
	move.l	(_expmem,pc),d0
	add.l	#STACKSIZE-6,d0
	move.l	d0,($5a1b8).l
	move.l	d0,($5a1da).l
	move.l	d0,($5a23c).l
.nostack
	move.w	#$2700,sr
	jmp	($4B100).l

_pl	PL_START
	PL_W	$716,DMAF_SETCLR|DMAF_MASTER	;game enables master DMA only
	PL_S	$1e30,8			;rom access
	PL_P	$205a,_subd0		;empty dbf loop
	PL_P	$29a6,_patch_aud1
	PL_P	$29bc,_patch_aud1
	PL_P	$29c6,_patch_aud1
	PL_P	$2ac0,_patch_vertb
	PL_P	$2c9e,_patch_vertb
	PL_P	$5e8a,_loadgame
	PL_P	$5f26,_savegame
	PL_P	$a858,_dmaon		;enable copper and bitplanes
	PL_END

; Reached from the frame publication routine's 34-byte copy (Disk.1 $5E4F6), which
; continues past the patch to $5A862. The original body copies six bytes and returns,
; dropping the copy's last 12 bytes, and waits for a vertical blank on every frame.
_dmaon	btst	#0,(_custom1+3,pc)
	beq.b	.orig
	move.l	a2,-(sp)
	lea	(_dmadone,pc),a2
	tst.b	(a2)
	bne.b	.copy
	st	(a2)
	move.w	#DMAF_SETCLR|DMAF_COPPER|DMAF_RASTER,(_custom+dmacon).l
	bsr.w	_waitvb
.copy	move.l	(sp)+,a2
	move.l	(a1)+,(a0)+	;the three replaced moves
	move.l	(a1)+,(a0)+
	move.l	(a1)+,(a0)+
	jmp	($5a85e).l	;the rest of the copy
.orig	move.w	#DMAF_SETCLR|DMAF_COPPER|DMAF_RASTER,(_custom+dmacon).l
	bsr.w	_waitvb
	move.l	(a1)+,(a0)+	;original
	move.w	(a1)+,(a0)+
	rts

_dmadone	dc.b	0
	EVEN

_diskload	moveq	#1,d2
	movea.l	(_resload,pc),a2
	jmp	(resload_DiskLoad,a2)

_patch_vertb	bsr.b	_checkkeyboard
	move.w	#INTF_VERTB,(_custom+intreq).l
	tst.w	_custom+intreqr
	rte

_patch_aud1	bsr.b	_checkkeyboard
	move.w	#INTF_AUD1,(_custom+intreq).l
	tst.w	_custom+intreqr
	rte

_int68	bsr.b	_checkkeyboard
	move.w	#INTF_PORTS,(_custom+intreq).l
	tst.w	_custom+intreqr
	rte

_checkkeyboard	movem.l	d0/d1/a0,-(sp)
	move.w	#(INTF_PORTS|INTF_SETCLR),(_custom+intena).l
	lea	(_ciaa).l,a0
	btst	#CIAICRB_SP,(ciaicr,a0)
	beq.b	.end
	move.w	#INTF_PORTS,(_custom+intreq).l
	move.b	(ciasdr,a0),d0
	ori.b	#CIACRAF_SPMODE,(ciacra,a0)
	move.w	d0,-(sp)
	ror.b	#1,d0
	not.b	d0
	cmp.b	(_keyexit,pc),d0
	beq.b	_quit
	cmpi.b	#$78,d0
	beq.b	_quit
	moveq	#2,d0
.wait1	move.b	(_custom+vhposr).l,d1
.wait2	cmp.b	(_custom+vhposr).l,d1
	beq.b	.wait2
	dbra	d0,.wait1
	andi.b	#$BF,(ciacra,a0)
	move.w	(sp)+,d0
	move.b	d0,(8).w
	moveq	#-1,d1
	move.b	d1,(9).w
.end	movem.l	(sp)+,d0/d1/a0
	rts

_quit	move.l	#$FFFFFFFF,-(sp)
	movea.l	(_resload,pc),a0
	jmp	(resload_Abort,a0)

_loadgame	movem.l	d0-d7/a0-a6,-(sp)
	movea.l	a0,a1
	clr.l	(a1)
	bsr.b	_setsavename
	move.l	a1,-(sp)
	jsr	(resload_GetFileSize,a2)
	movea.l	(sp)+,a1
	cmpi.l	#$2056,d0
	bne.b	lbC0003B0
	bsr.b	_setsavename
	jsr	(resload_LoadFile,a2)
lbC0003B0	move.w	#DMAF_AUD2,(_custom+dmacon).l
	moveq	#0,d0
	move.l	d0,(_custom+aud0+ac_vol).l
	move.l	d0,(_custom+aud1+ac_vol).l
	move.l	d0,(_custom+aud2+ac_vol).l
	move.l	d0,(_custom+aud3+ac_vol).l
	movem.l	(sp)+,d0-d7/a0-a6
	moveq	#0,d0
	rts

_savegame	movem.l	d0-d7/a0-a6,-(sp)
	bsr.b	_setsavename
	lea	($5550).w,a1
	move.l	#$2056,d0
	jsr	(resload_SaveFile,a2)
	movem.l	(sp)+,d0-d7/a0-a6
	jmp	($55EB4).l

_setsavename	move.b	($55F87).l,d0
	lsr.b	#1,d0
	subq.b	#1,d0
	ori.b	#$30,d0
	lea	(Mercenary3sav,pc),a0
	move.b	d0,(15,a0)
	movea.l	(_resload,pc),a2
	rts

_subd0	lsr.l	#3,d0
	move.l	d1,-(a7)
.1	move.b	($dff006),d1
.2	cmp.b	($dff006),d1
	beq.b	.2
	subq.l	#1,d0
	bne.b	.1
	move.l	(a7)+,d1
	move.l	d1,($72b0).w	;original
	rts			;original

_waitvb	btst	#0,(_custom+vposr+1).l
	beq.b	_waitvb
.1	btst	#0,(_custom+vposr+1).l
	bne.b	.1
	rts

_clist	dc.l	$8E2C81
	dc.l	$90F4C1
	dc.l	$920038
	dc.l	$9400D0
	dc.l	$1004200
	dc.l	$1020000
	dc.l	$1040000
	dc.l	$1080000
	dc.l	$10A0000
	dc.l	$E00004
	dc.l	$E28000
	dc.l	$E40004
	dc.l	$E6A000
	dc.l	$E80004
	dc.l	$EAC000
	dc.l	$EC0004
	dc.l	$EEE000
	dc.l	$FFFFFFFE

_tags	dc.l	WHDLTAG_ATTNFLAGS_GET
	dc.w	0
_attn	dc.w	0
	dc.l	WHDLTAG_CUSTOM1_GET
_custom1	dc.l	0
	dc.l	0

_resload	dc.l	0
	CNOP	0,4
