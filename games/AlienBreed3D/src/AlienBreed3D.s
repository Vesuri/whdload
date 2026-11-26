;*---------------------------------------------------------------------------
;  :Program.	AlienBreed3D.s
;  :Contents.	Slave for "Alien Breed 3D" (c) 1995 Team 17
;  :Author.	Psygore (slave 1.3, 08.01.2020)
;  :Note.	The install package's source (src/AlienBreed3DHD_src.lzx) is
;		XPK IDEA encrypted. This is a reconstruction from the shipped
;		AlienBreed3D.slave and, with NOMUSIC set,
;		AlienBreed3D_nomusic.slave; vasm rebuilds both byte for byte
;		with -no-opt. Labels and comments are ours. Lxxxx labels are
;		code-hunk offsets in AlienBreed3D.slave. ORIGINAL builds
;		Psygore's bytes; without it, Enhanced resolution (CUSTOM5,
;		palette.s) is added.
;---------------------------------------------------------------------------*

	INCLUDE	whdload.i

	IFND	NOMUSIC
CHIPPOOL	= $90000		;576 KB: the slave's chip pool ends here
	ELSE
CHIPPOOL	= $6b000		;428 KB: no HackAB3D
	ENDC
	IFD	ORIGINAL
CHIPMEM		= CHIPPOOL
EXPMEM		= $158000		;the game, its fast memory pool, the stacks
	ELSE
CHIPMEM		= CHIPPOOL+$27000	;and Enhanced resolution's screens (display.s)
	IFND	LORES
EXPMEM		= $20a000		;and its area, PA_SIZE (palette.s, display.s)
	ELSE
EXPMEM		= $1be000
	ENDC
	ENDC
SSP_OFF		= $157e00		;from ExpMem; USP 1 KB below

;======================================================================

base		moveq	#-1,d0
		rts
		dc.b	"WHDLOADS"		;ws_ID
		dc.w	18			;ws_Version
		dc.w	WHDLF_NoError|WHDLF_Req68020|WHDLF_ReqAGA	;ws_Flags
		dc.l	CHIPMEM			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	_start-base		;ws_GameLoader
		dc.w	_data-base		;ws_CurrentDir
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$59			;ws_keyexit = F10
_expmem		dc.l	EXPMEM			;ws_ExpMem
		dc.w	_name-base		;ws_name
		dc.w	_copy-base		;ws_copy
		dc.w	_info-base		;ws_info
		dc.w	0			;ws_kickname
		dc.l	0			;ws_kicksize
		dc.w	0			;ws_kickcrc
		dc.w	_config-base		;ws_config

	IFND	NOMUSIC
_name		dc.b	"Alien Breed 3D",0
	ELSE
_name		dc.b	"Alien Breed 3D (no music)",0
	ENDC
_copy		dc.b	"1995 Team 17",0
_info		dc.b	"Installed & fixed by Psygore",10
	IFD	ORIGINAL
		dc.b	"Version 1.3 (08 Jan 2020)",0
	ELSE
		dc.b	"Enhanced by Vesuri",10,10
		dc.b	"Version 2.0b (26.11.2026)",0
	IFND	NOMUSIC
		dc.b	"$VER: AlienBreed3D.slave 2.0b (26.11.2026)",0
	ELSE
		dc.b	"$VER: AlienBreed3D_nomusic.slave 2.0b (26.11.2026)",0
	ENDC
	ENDC
_data		dc.b	"data",0
_config		dc.b	"C1:X:Unlimited Energy:0;"
		dc.b	"C1:X:Unlimited Shots:1;"
		dc.b	"C1:X:Skip Levels (F1):2;"
		dc.b	"C2:L:Mouse Control:---,LMB=fwd/RMB=fire,RMB=fwd/LMB=fire;"
	IFND	NOMUSIC
		dc.b	"C3:B:Load Aminet version (abd8ch);"
		dc.b	"C4:B:Enable main music (HackAB3D) in the end part"
	ELSE
		dc.b	"C3:B:Load Aminet version (abd8ch)"
	ENDC
	IFND	ORIGINAL
		dc.b	";C5:B:Enhanced resolution"
	ENDC
		dc.b	0
; The game's files: the floppy/CD32 executable (packed or not), the Aminet 8-channel
; version, the Team 17 logo picture, the music for the end part, the saved settings.
_abd		dc.b	"abd",0
_abdpk		dc.b	"abd.pk",0
_abd8ch		dc.b	"abd8ch",0
_team		dc.b	"team",0
	IFND	NOMUSIC
_hackab3d	dc.b	"HackAB3D",0
	ENDC
_prefs		dc.b	"prefs",0
		EVEN

;======================================================================
; a0 = resload. Stacks at the top of ExpMem; caches per CPU; the interrupt handlers;
; the Team 17 picture; an exec and a dos library of ILLEGALs with the few functions the
; game calls; then the game, relocated, patched for its version and started.

_start
	lea	_resload(pc),a1
	move.l	a0,(a1)
	movea.l	a0,a2
	movea.l	_expmem(pc),a0
	adda.l	#1408512,a0
	movea.l	a0,sp
	lea	-1024(a0),a0
	move.l	a0,usp
	lea	_ctrltags(pc),a0
	jsr	resload_Control(a2)
	move.l	#810,d0
	move.l	_attnflags(pc),d1
	btst	#3,d1
	beq.s	.cpuset
	move.l	#15165,d0
.cpuset
	move.l	#32575,d1
	jsr	resload_SetCPU(a2)
	pea	_level2(pc)
	move.l	(sp)+,($68).w
	pea	_level3(pc)
	move.l	(sp)+,($6c).w
	pea	_level5(pc)
	move.l	(sp)+,($74).w
	IFND	NOMUSIC
	pea	_level6(pc)
	move.l	(sp)+,($78).w
	move.b	#-127,$bfdd00
	ENDC
	move.w	#-14248,$dff09a
	bsr.w	_showteam
	move.w	#-32736,$dff09a
	movea.l	_expmem(pc),a0
	move.w	#2047,d0
.exec
	move.w	#19196,(a0)+
	dbf	d0,.exec
	move.l	a0,($4).w
	move.w	#20217,-198(a0)
	pea	_allocmem(pc)
	move.l	(sp)+,-196(a0)
	move.w	#20217,-210(a0)
	pea	_freemem(pc)
	move.l	(sp)+,-208(a0)
	move.w	#20085,-132(a0)
	move.w	#20085,-138(a0)
	move.w	#20085,-150(a0)
	move.w	#20085,-156(a0)
	move.w	#2047,d0
.dos
	move.w	#19196,(a0)+
	dbf	d0,.dos
	lea	_dosbase(pc),a1
	move.l	a0,(a1)
	move.w	#20217,-30(a0)
	pea	_dos_open(pc)
	move.l	(sp)+,-28(a0)
	move.w	#20217,-42(a0)
	pea	_dos_read(pc)
	move.l	(sp)+,-40(a0)
	move.w	#20085,-36(a0)
	move.w	#20217,-390(a0)
	pea	_dos_examinefh(pc)
	move.l	(sp)+,-388(a0)
	move.w	#20085,-198(a0)
	lea	_expmem(pc),a0
	addi.l	#8192,(a0)
	bsr.w	_flushcache
	movea.l	_expmem(pc),a6
	IFND	NOMUSIC
	lea	_hackab3d(pc),a3
	movea.l	a3,a0
	jsr	resload_GetFileSize(a2)
	tst.l	d0
	beq.s	.nohack
	movea.l	a3,a0
	movea.l	a6,a1
	jsr	resload_LoadFileDecrunch(a2)
	lea	_chipfree(pc),a3
	move.l	(a3),d3
	movea.l	a6,a0
	lea	_reloctags(pc),a1
	jsr	resload_Relocate(a2)
	cmpi.w	#28709,18(a6)
	bne.s	.nohack
	lea	_fastfree(pc),a0
	lea	(0,a6,d0.l),a1
	move.l	a1,(a0)
	addq.l	#7,d3
	andi.b	#-8,d3
	add.l	d3,(a3)
	move.l	a6,d6
	addq.l	#4,d6
	lsr.l	#2,d6
	lea	_pl_hack(pc),a0
	movea.l	d6,a1
	jsr	resload_PatchSeg(a2)
	movem.l	a2/a6,-(sp)
	jsr	336(a6)
	movem.l	(sp)+,a2/a6
	lea	12288(a6),a6
.nohack
	ENDC
	pea	_abd8ch(pc)
	move.l	_custom3(pc),d0
	subq.l	#1,d0
	beq.s	.load
	addq.l	#4,sp
	pea	_abdpk(pc)
	movea.l	(sp),a0
	jsr	resload_GetFileSize(a2)
	tst.l	d0
	bne.s	.load
	addq.l	#4,sp
	pea	_abd(pc)
	movea.l	(sp),a0
	jsr	resload_GetFileSize(a2)
	tst.l	d0
	bne.s	.load
	addq.l	#4,sp
	pea	_abd8ch(pc)
.load
	movea.l	(sp)+,a0
	movea.l	a6,a1
	jsr	resload_LoadFileDecrunch(a2)
	movea.l	a6,a0
	jsr	resload_CRC16(a2)
	lea	_gameptrs(pc),a0
	move.l	a6,(a0)
	move.l	a6,4(a0)
	move.l	a6,8(a0)
	move.l	a6,12(a0)
	move.l	a6,16(a0)
	move.l	a6,20(a0)
	move.l	#281004,d1
	move.l	#281006,d2
	move.l	#281008,d3
	move.l	#25116,d4
	move.l	#292154,d5
	move.l	#279786,d6
	lea	_pl_v1(pc),a4
	cmpi.w	#9170,d0
	beq.s	.version
	move.l	#282474,d1
	move.l	#282476,d2
	move.l	#282478,d3
	move.l	#25312,d4
	move.l	#293736,d5
	move.l	#281172,d6
	lea	_pl_v2(pc),a4
	cmpi.w	#-648,d0
	beq.s	.version
	move.l	#281714,d1
	move.l	#281716,d2
	move.l	#281718,d3
	move.l	#25660,d4
	move.l	#292864,d5
	move.l	#280438,d6
	lea	_pl_v3(pc),a4
	cmpi.w	#-15140,d0
	bne.w	_wrongver
.version
	add.l	d1,(a0)
	add.l	d2,4(a0)
	add.l	d3,8(a0)
	add.l	d4,12(a0)
	add.l	d5,16(a0)
	add.l	d6,20(a0)
	lea	_chipfree(pc),a3
	move.l	(a3),d3
	movea.l	a6,a0
	lea	_reloctags(pc),a1
	jsr	resload_Relocate(a2)
	lea	_fastfree(pc),a0
	lea	(0,a6,d0.l),a1
	move.l	a1,(a0)
	addq.l	#7,d3
	addq.l	#8,d3
	andi.b	#-8,d3
	add.l	d3,(a3)
	move.l	#8192,d0
	bsr.w	_initmem
	bsr.s	_loadprefs
	movea.l	a4,a0
	move.l	a6,d6
	addq.l	#4,d6
	lsr.l	#2,d6
	movea.l	d6,a1
	jsr	resload_PatchSeg(a2)
	suba.l	a0,a0
	move.w	#-31776,$dff096
	jmp	8(a6)
_p_check
	tst.b	80(a5)
	bne.s	L045c
	tst.b	69(a5)
	beq.s	L046a
	rts
L045c
	move.l	a0,-(sp)
	movea.l	4(sp),a0
	movea.l	96(a0),a0
	clr.w	(a0)
	movea.l	(sp)+,a0
L046a
	addi.l	#28,(sp)
	rts
_p_boundsl13
	addq.l	#2,(sp)
	movem.l	d1/a1,-(sp)
	andi.l	#16777215,d1
	adda.l	d1,a0
	movea.l	_expmem(pc),a1
	adda.l	#1388544,a1
	cmpa.l	a0,a1
	bcc.s	L0496
	addi.l	#44,8(sp)
L0496
	movem.l	(sp)+,d1/a1
	rts
_p_boundsread
	sub.w	d0,d1
	bge.s	L04a4
L04a0
	addq.l	#4,sp
	rts
L04a4
	cmpi.w	#512,d1
	bcc.s	L04a0
	rts
_loadprefs
	movem.l	d0-d2/a0-a3,-(sp)
	lea	_prefs(pc),a0
	movea.l	a0,a3
	movea.l	_resload(pc),a2
	jsr	resload_GetFileSize(a2)
	tst.l	d0
	beq.s	_noprefs
	movea.l	a3,a0
	movea.l	_gameptrs(pc),a1
	movea.l	_resload(pc),a2
	jsr	resload_LoadFileDecrunch(a2)
	moveq	#0,d0
	moveq	#0,d1
	movea.l	L0534(pc),a0
	movea.l	L0538(pc),a1
	movea.l	_gameptrs(pc),a2
L04e0
	move.w	d0,d2
	muls.w	#40,d2
	move.b	(a2)+,d1
	move.l	(0,a1,d1.w*4),(32,a0,d2.w)
	addq.w	#1,d0
	cmpi.w	#12,d0
	bne.s	L04e0
_noprefs
	movem.l	(sp)+,d0-d2/a0-a3
	rts
_p_saveprefs
	addq.l	#2,(sp)
	cmpi.w	#12,d0
	beq.s	L0506
	rts
L0506
	addq.l	#4,sp
	movem.l	d0-d2/a0-a2,-(sp)
	moveq	#12,d0
	lea	_prefs(pc),a0
	movea.l	_gameptrs(pc),a1
	movea.l	_resload(pc),a2
	jsr	resload_SaveFile(a2)
	movem.l	(sp)+,d0-d2/a0-a2
	rts
_gameptrs
	dc.l	$0
L0528
	dc.l	$0
L052c
	dc.l	$0
L0530
	dc.l	$0
L0534
	dc.l	$0
L0538
	dc.l	$0
_pl_v1
	PL_START
	PL_IFC1X	2
	PL_PS	$3d4e,_p_check
	PL_ENDIF
	PL_IFC1X	0
	PL_S	$5484,$6
	PL_ENDIF
	PL_IFC1X	1
	PL_NOP	$bff4,$2
	PL_ENDIF
	PL_IFC2
	PL_NOP	$814a,$4
	PL_PS	$3fd1c,_p_control
	PL_S	$3fd22,$2e0
	PL_ENDIF
	PL_S	$78,$6
	PL_S	$8a,$6
	PL_B	$5b63,$ffff
	PL_PS	$30,_p_setvblcb
	PL_PS	$3e,_p_setkeycb
	PL_S	$44,$34
	PL_S	$29d2,$c
	PL_PS	$30a0,_flushcache
	PL_S	$30a6,$8
	PL_S	$30bc,$26
	PL_PS	$3e16,_waitvbl
	PL_S	$8d5e,$1a
	PL_PS	$8d96,_p_readjoyport
	PL_PS	$8f9a,_p_readjoyport
	PL_L	$1931e,$6430020
	PL_NOP	$19322,$2
	PL_PS	$19860,_p_boundsread
	PL_PS	$2177c,_p_boundsl13
	PL_PS	$44708,_p_dosbase
	PL_R	$44adc
	PL_PS	$453c4,_p_saveprefs
	PL_PS	$4564c,_p_vhposr
	IFND	NOMUSIC
	PL_PS	$43414,_p_musicoff
	PL_PS	$48e86,_p_musicon
	ENDC
	PL_NOP	$4507e,$2
	PL_B	$45086,$60
	PL_W	$5b5a,$ffff
	PL_S	$1f158,$e
	PL_P	$1f1d2,_p_flushjsr
	PL_PS	$9ca40,_p_setcop2
	PL_R	$9caac
	PL_W	$9cf82,$200
	PL_PS	$9d398,_p_waitlines
	PL_PS	$9d3bc,_p_waitlines
	PL_PS	$af74c,_p_dosbase
	PL_NOP	$af752,$2
	PL_NOP	$af7b2,$4
	PL_PS	$af7b6,_endcopper
	PL_P	$af7e8,_endpart
	PL_END
_waitvbl
	lea	16640(a3),a3
L0698
	btst	#0,$dff005
	beq.s	L0698
L06a2
	btst	#0,$dff005
	bne.s	L06a2
	rts
_pl_v2
	PL_START
	PL_IFC1X	2
	PL_PS	$3db0,_p_check
	PL_ENDIF
	PL_IFC1X	0
	PL_S	$5548,$6
	PL_ENDIF
	PL_IFC1X	1
	PL_NOP	$c3de,$2
	PL_ENDIF
	PL_IFC2
	PL_NOP	$820e,$4
	PL_PS	$4021c,_p_control
	PL_S	$40222,$2e0
	PL_ENDIF
	PL_PS	$68,_p_setvblcb
	PL_PS	$76,_p_setkeycb
	PL_S	$7c,$34
	PL_S	$2a26,$c
	PL_PS	$30e4,_flushcache
	PL_S	$30ea,$8
	PL_S	$3100,$26
	PL_PS	$3e90,_waitvbl
	PL_R	$8d98
	PL_S	$9136,$1a
	PL_PS	$916e,_p_readjoyport
	PL_PS	$9372,_p_readjoyport
	PL_L	$1985e,$6430020
	PL_NOP	$19862,$2
	PL_PS	$19da0,_p_boundsread
	PL_PS	$21c7c,_p_boundsl13
	PL_PS	$44c7e,_p_dosbase
	PL_PS	$459ec,_p_saveprefs
	PL_PS	$45c7a,_p_vhposr
	IFND	NOMUSIC
	PL_PS	$43990,_p_musicoff
	PL_PS	$496c0,_p_musicon
	ENDC
	PL_NOP	$456a0,$2
	PL_B	$456a8,$60
	PL_W	$5c1e,$ffff
	PL_S	$1f658,$e
	PL_P	$1f6d2,_p_flushjsr
	PL_PS	$9d080,_p_setcop2
	PL_R	$9d0ec
	PL_W	$9d5c2,$200
	PL_PS	$9d9d8,_p_waitlines
	PL_PS	$9d9fc,_p_waitlines
	PL_PS	$b123e,_p_dosbase
	PL_NOP	$b1244,$2
	PL_NOP	$b12a4,$4
	PL_PS	$b12a8,_endcopper
	PL_P	$b12da,_endpart
	PL_END
_pl_v3
	PL_START
	PL_IFC1X	2
	PL_PS	$3d90,_p_check
	PL_ENDIF
	PL_IFC1X	0
	PL_S	$56a4,$6
	PL_ENDIF
	PL_IFC1X	1
	PL_W	$c20c,$4e71
	PL_ENDIF
	PL_IFC2
	PL_NOP	$836a,$4
	PL_PS	$3ff96,_p_control
	PL_S	$3ff9c,$2e0
	PL_ENDIF
	PL_S	$78,$6
	PL_S	$8a,$6
	PL_B	$5d83,$ffff
	PL_PS	$30,_p_setvblcb
	PL_PS	$3e,_p_setkeycb
	PL_S	$44,$34
	PL_S	$29ca,$c
	PL_PS	$30e8,_flushcache
	PL_S	$30ee,$8
	PL_S	$3104,$26
	PL_PS	$3e58,_waitvbl
	PL_S	$8f72,$1a
	PL_PS	$8faa,_p_readjoyport
	PL_PS	$91ae,_p_readjoyport
	PL_L	$195c6,$6430020
	PL_NOP	$195ca,$2
	PL_PS	$19b08,_p_boundsread
	PL_PS	$219f6,_p_boundsl13
	PL_PS	$449a0,_p_dosbase
	PL_R	$44da2
	PL_PS	$4568a,_p_saveprefs
	PL_PS	$45912,_p_vhposr
	IFND	NOMUSIC
	PL_PS	$436a0,_p_musicoff
	PL_PS	$4914c,_p_musicon
	ENDC
	PL_NOP	$45344,$2
	PL_B	$4534c,$60
	PL_W	$5d7a,$ffff
	PL_S	$1f3d8,$e
	PL_P	$1f452,_p_flushjsr
	PL_PS	$9ad00,_p_setcop2
	PL_R	$9ad6c
	PL_W	$9b242,$200
	PL_PS	$9b658,_p_waitlines
	PL_PS	$9b67c,_p_waitlines
	IFND	ORIGINAL
	PL_IFC5
	PL_PS	$44aa4,_p_loaded	;the palette (palette.s)
	PL_PS	$4463e,_p_coplists	;the display (display.s): the game's lists in fast
	PL_S	$44644,$2e
	PL_R	$43c40			;and not freed
	PL_PS	$31a0,_p_cop1		;the new screens' heads instead of the template
	PL_S	$31a6,4
	PL_PS	$32d2,_p_show		;each swap: the frame onto a screen
	PL_PS	$3e42,_p_show
	PL_PS	$8e5e,_p_show
	INCLUDE	stride.s		;lines of DS_STRIDE bytes (display.s)
	PL_L	$6910,60*DS_STRIDE	;water tint: adda.l #24960, 60 lines
	PL_W	$1935e,DS_STRIDE	;sky: adda.w #416, its first row
	IFND	LORES			;the 1x1 renderer (hires.s)
	PL_PS	$1a616,_t_column	;walls: a column's slot, any width
	PL_S	$1a61c,4
	PL_PS	$1a3ac,_t_column	;see-through walls
	PL_S	$1a3b2,4
	PL_PS	$1cb8a,_t_strip		;a wall strip's line and texture step
	PL_S	$1cb90,8
	PL_PS	$1cf18,_t_strip
	PL_S	$1cf1e,8
	PL_PS	$1d13a,_t_walltop	;a wall's top and bottom above the eye
	PL_PS	$1d146,_t_wallbot
	PL_PS	$1b3b0,_t_walltop	;a curved wall's
	PL_PS	$1b3b6,_t_wallbot
	PL_PS	$2142e,_t_eye6		;glass and bitmaps: zone clips above the eye
	PL_PS	$21452,_t_eye6
	PL_PS	$21770,_t_eye6
	PL_PS	$21794,_t_eye6
	PL_PS	$2147a,_t_eye2		;their heights, and a polygon object's
	PL_PS	$21864,_t_eye2
	PL_PS	$21e28,_t_eye2
	PL_PS	$2149a,_t_size		;glass and bitmaps: their size
	PL_NOP	$214a0,2
	PL_PS	$21884,_t_size
	PL_NOP	$2188a,2
	PL_PS	$221c6,_t_poly		;the polygons' lines
	PL_NOP	$221cc,2
	PL_PS	$2271c,_t_polyh
	PL_NOP	$22722,2
	PL_PS	$22466,_t_polyg
	PL_NOP	$2246c,2
	PL_W	$220ec,-EDGE_STRIDE	;the polygons' top edges, -1536(a4) from the
	PL_W	$22126,-EDGE_STRIDE+2	;bottom's: our edges (hires.s DA_EDGES)
	PL_W	$2212a,-EDGE_STRIDE+4
	PL_W	$223ac,-EDGE_STRIDE
	PL_W	$223dc,-EDGE_STRIDE+2
	PL_W	$223e0,-EDGE_STRIDE+4
	PL_W	$2269a,-EDGE_STRIDE
	PL_W	$226c6,-EDGE_STRIDE+2
	PL_W	$226ca,-EDGE_STRIDE+4
	PL_P	$1fbf6,_t_split		;FloorLine: a span over any number of banks
	PL_PS	$84aa,_t_x128		;x * 128 * S: the level's points
	PL_NOP	$84b0,2
	PL_PS	$8a76,_t_x128		;the objects'
	PL_NOP	$8a7c,2
	PL_PS	$1fb96,_t_fstep		;FloorLine: the steps / S
	PL_S	$1fb9c,10
	PL_PS	$1fbc4,_t_fstep2
	PL_PS	$214dc,_t_index		;glass and bitmaps: the texture step / S
	PL_PS	$214f6,_t_index
	PL_PS	$218f8,_t_index
	PL_PS	$21914,_t_index
	PL_PS	$21dd6,_t_pvert		;a polygon object's vertices times S
	PL_S	$21ddc,4
	PL_W	$1d8e8,2*SIDE_STRIDE	;the floors' edges: leftbrighttab from
	PL_W	$1d9cc,2*SIDE_STRIDE	;leftsidetab (hires.s DA_SIDES),
	PL_W	$1f17c,SIDE_STRIDE	;rightsidetab,
	PL_W	$1f1d6,SIDE_STRIDE	;(flat floors, water, inside the zone)
	PL_W	$1f226,SIDE_STRIDE
	PL_W	$1f320,SIDE_STRIDE
	PL_W	$1f276,2*SIDE_STRIDE	;leftbrighttab,
	PL_W	$1f342,2*SIDE_STRIDE
	PL_W	$1f28c,3*SIDE_STRIDE	;rightbrighttab
	PL_W	$1f358,3*SIDE_STRIDE
	PL_PS	$5826,_t_gun		;gun: ours SxS
	PL_P	$1933e,_t_sky		;the sky SxS
	PL_P	$6900,_t_water		;the water tint
	PL_P	$41b2,_t_pause		;the pause screen SxS
	ELSE
	PL_W	$582a,DS_STRIDE		;gun: muls #416, its first row
	ENDC
	PL_ENDIF
	ENDC
	PL_END
_endcopper
	lea	($1000).w,a1
	movea.l	a1,a0
	move.l	#16777728,(a0)+
	move.l	#17173504,(a0)+
	move.l	#25165824,(a0)+
	move.l	#-2,(a0)+
	move.l	a1,$dff080
	move.w	d0,$dff088
	IFND	NOMUSIC
	lea	$8f000,a0
	ELSE
	lea	$6a000,a0
	ENDC
	move.l	#12288,d0
L0958
	clr.l	-(a0)
	clr.l	-(a0)
	clr.l	-(a0)
	clr.l	-(a0)
	subq.l	#1,d0
	bne.s	L0958
	move.l	a0,d0
	lea	_chiptop(pc),a0
	move.l	d0,(a0)
	rts
_chiptop
	dc.l	$0
_showteam
	movea.l	_resload(pc),a2
	lea	$40000,a3
	lea	($1000).w,a4
	lea	$dff000,a5
	lea	_team(pc),a0
	movea.l	a3,a1
	jsr	resload_LoadFileDecrunch(a2)
	movea.l	a3,a0
	jsr	resload_CRC16(a2)
	movea.l	a3,a0
	suba.l	a1,a1
	jsr	resload_Relocate(a2)
	movea.l	a4,a1
	move.l	#9314433,(a1)+
	move.l	#9445569,(a1)+
	move.l	#9568312,(a1)+
	move.l	#9699488,(a1)+
	move.l	#17301504,(a1)+
	move.l	#17432576,(a1)+
	lea	270(a3),a0
	move.w	#224,d1
	moveq	#7,d7
L09ce
	move.l	(a0)+,d0
	swap	d0
	move.w	d1,(a1)+
	addq.w	#2,d1
	move.w	d0,(a1)+
	swap	d0
	move.w	d1,(a1)+
	addq.w	#2,d1
	move.w	d0,(a1)+
	dbf	d7,L09ce
	lea	366(a3),a0
	move.l	#17170432,d2
	moveq	#7,d6
L09f0
	move.l	d2,(a1)+
	moveq	#31,d7
	move.w	#384,d1
L09f8
	move.w	d1,(a1)+
	move.w	(a0)+,(a1)+
	addq.w	#2,d1
	dbf	d7,L09f8
	addi.w	#8192,d2
	dbf	d6,L09f0
	move.l	#33292303,(a1)+
	move.l	#16777744,(a1)+
	move.l	#-2,(a1)+
L0a1c
	btst	#0,$dff005
	beq.s	L0a1c
L0a26
	btst	#0,$dff005
	bne.s	L0a26
	move.l	a4,128(a5)
	move.w	d0,136(a5)
	move.w	#-31808,150(a5)
	moveq	#40,d0
	jsr	resload_Delay(a2)
	move.w	#32767,150(a5)
	movea.l	a4,a0
	move.l	#16777728,(a0)+
	move.l	#-2,(a0)+
	move.l	a4,128(a5)
	move.w	d0,136(a5)
	rts
_endpart
	lea	($1000).w,a4
	lea	$dff000,a5
	lea	_endcop_bpl(pc),a0
	move.l	_chiptop(pc),d4
	move.w	d4,4(a0)
	swap	d4
	move.w	d4,(a0)
	swap	d4
	lea	_endcop(pc),a0
	movea.l	a4,a1
	move.w	#71,d0
L0a88
	move.b	(a0)+,(a1)+
	dbf	d0,L0a88
L0a8e
	btst	#0,$dff005
	beq.s	L0a8e
L0a98
	btst	#0,$dff005
	bne.s	L0a98
	move.l	a4,128(a5)
	move.w	d0,136(a5)
	IFND	NOMUSIC
	move.l	_custom4(pc),d0
	subq.l	#1,d0
	bne.s	L0acc
	tst.l	_replay(pc)
	beq.s	L0acc
	movem.l	d0-a6,-(sp)
	movea.l	_expmem(pc),a0
	jsr	348(a0)
	bsr.w	_p_musicon
	movem.l	(sp)+,d0-a6
L0acc
	ENDC
	move.l	d4,d0
	moveq	#80,d2
	moveq	#0,d3
	move.l	d4,d1
	addi.l	#121920,d1
L0ada
	btst	#6,$bfe001
	beq.s	L0aea
	cmpi.w	#5,d3
	bne.s	L0afa
L0aea
	moveq	#0,d3
	add.l	d2,d0
	move.w	d0,62(a4)
	swap	d0
	move.w	d0,58(a4)
	swap	d0
L0afa
	addq.w	#1,d3
L0afc
	btst	#0,$dff005
	beq.s	L0afc
L0b06
	btst	#0,$dff005
	bne.s	L0b06
L0b10
	btst	#7,$bfe001
	beq.s	L0b10
L0b1a
	btst	#2,$dff016
	beq.s	L0b1a
	cmp.l	d1,d0
	ble.s	L0ada
L0b28
	btst	#6,$bfe001
	bne.s	L0b28
	btst	#2,$dff016
	bne.s	L0b28
	bra.w	_exit
_endcop
	dc.w	$96
	dc.w	$120
	dc.w	$2001
	dc.w	$fffe
	dc.w	$96
	dc.w	$8100
	dc.w	$8e
	dc.w	$1581
	dc.w	$90
	dc.w	$40fe
	dc.w	$92
	dc.w	$3c
	dc.w	$94
	dc.w	$d4
	dc.w	$100
	dc.w	$9200
	dc.w	$106
	dc.w	$c00
	dc.w	$108
	dc.w	$0
	dc.w	$10a
	dc.w	$0
	dc.w	$10c
	dc.w	$11
	dc.w	$180
	dc.w	$0
	dc.w	$182
	dc.w	$fff
	dc.w	$e0
_endcop_bpl
	dc.w	$4
	dc.w	$e2
	dc.w	$0
	dc.w	$1fc
	dc.w	$0
	dc.w	$ffff
	dc.w	$fffe
_p_control
	movem.l	d0-d1/d7-a0/a5,-(sp)
	movea.l	L0530(pc),a5
	move.l	_custom2(pc),d1
	subq.l	#2,d1
	moveq	#0,d7
	movea.l	L0528(pc),a0
	move.b	(a0),d7
	cmpi.b	#-1,(0,a5,d7.w)
	beq.s	L0bc6
	btst	#2,$dff016
	seq	d0
	tst.l	d1
	beq.s	L0bbe
	btst	#6,$bfe001
	seq	d0
L0bbe
	andi.b	#15,d0
	move.b	d0,(0,a5,d7.w)
L0bc6
	movea.l	L052c(pc),a0
	move.b	(a0),d7
	cmpi.b	#-1,(0,a5,d7.w)
	beq.s	L0bf4
	btst	#6,$bfe001
	seq	d0
	tst.l	d1
	beq.s	L0bec
	btst	#2,$dff016
	seq	d0
L0bec
	andi.b	#15,d0
	move.b	d0,(0,a5,d7.w)
L0bf4
	movem.l	(sp)+,d0-d1/d7-a0/a5
	rts
_p_setvblcb
	lea	_vblcb(pc),a0
	move.l	18(a1),(a0)
	bra.w	_flushcache
_p_setkeycb
	lea	_keycb(pc),a0
	move.l	18(a1),(a0)
	bra.w	_flushcache
_p_waitlines
	moveq	#5,d0
L0c14
	move.b	$dff006,d1
L0c1a
	cmp.b	$dff006,d1
	beq.s	L0c1a
	dbf	d0,L0c14
	addi.l	#10,(sp)
	rts
_p_setcop2
	move.l	d0,$dff084
	rts
_p_vhposr
	move.w	$dff006,d0
	addq.l	#4,(sp)
	rts
_p_flushjsr
	bsr.w	_flushcache
	jsr	(a1)
	move.w	d4,(0,a1,d3.w*4)
	rts
_p_dosbase
	move.l	_dosbase(pc),d0
	rts
_dosbase
	ori.b	#0,d0
_dos_open
	move.l	d1,d0
	rts
_dos_read
	movem.l	d0-d2/a0-a2,-(sp)
	movea.l	d1,a0
	movea.l	d2,a1
	bsr.s	_skipvol
	movea.l	_resload(pc),a2
	jsr	resload_LoadFileDecrunch(a2)
	movem.l	(sp)+,d0-d2/a0-a2
	rts
_skipvol
	cmpi.b	#58,5(a0)
	bne.s	L0c7c
	addq.l	#6,a0
L0c7c
	rts
_dos_examinefh
	movem.l	d0-d2/a0-a2/a5,-(sp)
	movea.l	d1,a0
	movea.l	d2,a5
	bsr.s	_skipvol
	movea.l	_resload(pc),a2
	jsr	resload_GetFileSizeDec(a2)
	move.l	d0,124(a5)
	movem.l	(sp)+,d0-d2/a0-a2/a5
	rts
_level3
	movem.l	d0-a6,-(sp)
	lea	$dff000,a0
	move.w	30(a0),d0
	andi.w	#112,d0
	and.w	28(a0),d0
	beq.s	_l3end
	btst	#4,d0
	bne.s	L0cc6
	btst	#5,d0
	bne.s	L0ce0
	move.w	#64,156(a0)
	bra.s	_l3end
L0cc6
	move.w	#16,156(a0)
	movem.l	d0/a0,-(sp)
	move.l	_vblcb(pc),d0
	beq.s	L0cda
	movea.l	d0,a0
	jsr	(a0)
L0cda
	movem.l	(sp)+,d0/a0
	bra.s	_l3end
L0ce0
	move.w	#32,156(a0)
	moveq	#1,d0
	bsr.w	_readjoyport
	lea	_joypad(pc),a0
	move.l	d0,(a0)
	lea	_quitcount(pc),a0
	cmpi.w	#50,(a0)
	beq.w	_exit
	addq.w	#1,(a0)
	andi.l	#16646144,d0
	cmpi.l	#917504,d0
	beq.s	_l3end
	clr.w	(a0)
_l3end
	tst.w	$dff002
	movem.l	(sp)+,d0-a6
	rte
_quitcount
	dc.w	$0
_joypad
	dc.l	$0
_vblcb
	dc.l	$0
_level5
	movem.l	d0-a6,-(sp)
	lea	$dff000,a0
	move.w	30(a0),d0
	andi.w	#2048,d0
	and.w	28(a0),d0
	beq.s	L0d44
	move.w	#2048,156(a0)
L0d44
	tst.w	2(a0)
	movem.l	(sp)+,d0-a6
	rte
	IFND	NOMUSIC
_p_ispal
	ENDC
	move.l	_monitor(pc),d0
	cmpi.l	#135168,d0
	rts
	IFND	NOMUSIC
_pl_hack
	PL_START
	PL_PS	$1516,_p_ispal
	PL_PS	$152e,_p_hackint
	PL_S	$1534,$50
	PL_END
_p_musicon
	move.l	a0,-(sp)
	lea	_musicon(pc),a0
	move.w	#1,(a0)
	movea.l	(sp)+,a0
	rts
_p_musicoff
	move.l	a0,-(sp)
	lea	_musicon(pc),a0
	clr.w	(a0)
	lea	$dff000,a0
	clr.w	168(a0)
	clr.w	184(a0)
	clr.w	200(a0)
	clr.w	216(a0)
	move.w	#15,150(a0)
	movea.l	(sp)+,a0
	rts
_musicon
	dc.w	$1
_p_hackint
	lea	_replay(pc),a0
	move.l	48(a4),(a0)+
	move.l	44(a4),(a0)
	move.w	#-8192,$dff09a
	moveq	#8,d3
	rts
_level6
	movem.l	d0-a6,-(sp)
	lea	$dff000,a0
	move.w	30(a0),d0
	andi.w	#8192,d0
	and.w	28(a0),d0
	beq.s	L0e02
	btst	#0,$bfdd00
	beq.s	L0df4
	move.w	_musicon(pc),d0
	beq.s	L0df4
	move.l	_replay(pc),d0
	beq.s	L0df4
	movea.l	d0,a0
	movea.l	_replaydata(pc),a1
	jsr	(a0)
L0df4
	move.w	#8192,$dff09c
	tst.w	$dff002
L0e02
	movem.l	(sp)+,d0-a6
	rte
_replay
	dc.l	$0
_replaydata
	dc.l	$0
	ENDC
_flushcache
	move.l	_resload(pc),-(sp)
	addi.l	#32,(sp)
	rts
_level2
	movem.l	d0-a6,-(sp)
	lea	$dff000,a0
	lea	$bfe001,a1
	btst	#3,31(a0)
	beq.s	L0e5c
	btst	#3,3328(a1)
	beq.s	L0e5c
	bsr.s	_readkey
	cmp.b	_keyexit(pc),d0
	beq.w	_exit
	cmp.b	_keydebug(pc),d0
	beq.w	_debug
	move.l	a0,-(sp)
	move.l	_keycb(pc),d0
	beq.s	L0e5a
	movea.l	d0,a0
	jsr	(a0)
L0e5a
	movea.l	(sp)+,a0
L0e5c
	move.w	#8,156(a0)
	tst.w	2(a0)
	movem.l	(sp)+,d0-a6
	rte
_keycb
	dc.l	$0
_readkey
	moveq	#0,d0
	move.b	3072(a1),d0
	not.b	d0
	ror.b	#1,d0
	ori.b	#64,3584(a1)
	move.l	d0,-(sp)
	moveq	#2,d1
L0e84
	move.b	6(a0),d0
L0e88
	cmp.b	6(a0),d0
	beq.s	L0e88
	dbf	d1,L0e84
	move.l	(sp)+,d0
	andi.b	#-65,3584(a1)
	rts
_readjoyport
	bra.s	L0eb2
	dc.b	"$Id: 2018/07/01 $",10,0
	dc.b	0
L0eb2
	movem.l	d1-d6/a0-a2,-(sp)
	lea	$dff000,a0
	lea	$bfe001,a1
	tst.l	d0
	beq.s	L0ed0
	subq.l	#1,d0
	beq.s	L0ee4
	moveq	#0,d0
	bra.w	L0f98
L0ed0
	moveq	#6,d3
	moveq	#10,d4
	move.w	#-2560,d5
	move.w	10(a0),d6
	lea	_port0(pc),a2
	moveq	#8,d1
	bra.s	L0ef6
L0ee4
	moveq	#7,d3
	moveq	#14,d4
	move.w	#28416,d5
	move.w	12(a0),d6
	lea	_port1(pc),a2
	moveq	#12,d1
L0ef6
	moveq	#0,d2
	btst	d3,(a1)
	bne.s	L0f00
	bset	#22,d2
L0f00
	move.w	22(a0),d0
	btst	d4,d0
	bne.s	L0f0c
	bset	#23,d2
L0f0c
	btst	d1,d0
	bne.s	L0f14
	bset	#17,d2
L0f14
	move.w	d6,d0
	bsr.w	_cd32bits
	beq.s	L0f22
	move.w	#8203,(a2)
	bra.s	L0f9e
L0f22
	move.w	d0,d2
	moveq	#0,d0
	tst.b	1(a2)
	bne.s	L0f80
	bset	d3,512(a1)
	bclr	d3,(a1)
	move.w	d5,52(a0)
	moveq	#8,d1
	bra.s	L0f3e
L0f3a
	tst.b	(a1)
	tst.b	(a1)
L0f3e
	tst.b	(a1)
	tst.b	(a1)
	tst.b	(a1)
	tst.b	(a1)
	tst.b	(a1)
	tst.b	(a1)
	move.w	22(a0),d5
	bset	d3,(a1)
	bclr	d3,(a1)
	btst	d4,d5
	bne.s	L0f58
	bset	d1,d0
L0f58
	dbf	d1,L0f3a
	move.w	#-256,52(a0)
	bclr	d3,512(a1)
	lsr.w	#1,d0
	bne.s	L0f72
	bcc.s	L0f78
	move.w	#4096,(a2)
	bra.s	L0f8c
L0f72
	cmpi.w	#4096,(a2)
	beq.s	L0f8c
L0f78
	move.b	#48,(a2)
	andi.w	#128,d0
L0f80
	cmpi.b	#32,(a2)
	beq.s	L0f9e
	cmpi.b	#48,(a2)
	beq.s	L0fba
L0f8c
	ori.w	#4096,d0
L0f90
	move.w	d6,2(a2)
	swap	d0
	or.l	d2,d0
L0f98
	movem.l	(sp)+,d1-d6/a0-a2
	rts
L0f9e
	cmp.w	2(a2),d6
	beq.s	L0faa
	subq.b	#1,1(a2)
	blt.s	L0fb2
L0faa
	move.w	#8192,d0
	move.w	d6,d2
	bra.s	L0f90
L0fb2
	move.w	#12288,d0
	move.w	d0,(a2)
	bra.s	L0f90
L0fba
	subq.b	#1,1(a2)
	bge.s	L0fc6
	move.b	#10,1(a2)
L0fc6
	ori.w	#12288,d0
	bra.s	L0f90
_cd32bits
	move.w	d0,d1
	lsr.w	#1,d0
	eor.w	d0,d1
	andi.w	#257,d0
	andi.w	#257,d1
	ror.b	#1,d0
	ror.b	#1,d1
	lsr.w	#7,d0
	lsr.w	#5,d1
	or.w	d1,d0
	moveq	#-5,d1
	and.b	d0,d1
	lsr.b	#1,d1
	and.b	d0,d1
	rts
_port0
	dc.l	$0
_port1
	dc.l	$0
_p_readjoyport
	addq.l	#2,(sp)
	move.l	_joypad(pc),d0
	rts
_wrongver
	pea	($9).w
	bra.s	_abort
_debug
	pea	($5).w
	bra.s	_abort
_exit
	pea	(-$1).w
_abort
	move.l	_resload(pc),-(sp)
	addq.l	#4,(sp)
	rts
_reloctags
	dc.l	$88100000
_chipfree
	dc.l	$2000
	dc.l	$88100002
	dc.l	$8
	dc.l	$88100003
	dc.l	$ffffffff
	dc.l	$0
_fastfree
	dc.l	$0
_initmem
	lea	_fastfree(pc),a0
	tst.l	(a0)
	beq.s	L104e
	move.l	#1404928,d1
	sub.l	d0,d1
	add.l	_expmem(pc),d1
	move.l	d1,d0
	bsr.s	_initregion
L104e
	lea	_chipfree(pc),a0
	IFND	NOMUSIC
	moveq	#9,d0
	swap	d0
	ELSE
	move.l	#438272,d0
	ENDC
	bsr.s	_initregion
	bra.w	_flushcache
_initregion
	move.l	(a0),d1
	movea.l	d1,a0
	addq.l	#4,d1
	addq.l	#7,d1
	andi.b	#-8,d1
	movea.l	d1,a1
	move.l	d1,(a0)
	sub.l	d1,d0
	move.l	d0,4(a1)
	clr.l	(a1)
	rts
_allocmem
	lea	_fastfree(pc),a0
	tst.l	(a0)
	beq.s	L1086
	movea.l	(a0),a0
	btst	#1,d1
	beq.s	L108e
L1086
	bset	#1,d1
	movea.l	_chipfree(pc),a0
L108e
	movem.l	d0-d1,-(sp)
	bsr.s	_allocate
	movea.l	(sp)+,a0
	move.l	(sp)+,d1
	tst.l	d0
	bne.s	L10a8
	btst	#1,d1
	bne.w	_nochip
	bra.w	_nofast
L10a8
	btst	#16,d1
	beq.s	L10bc
	move.l	a0,d1
	lsr.l	#2,d1
	beq.s	L10bc
	movea.l	d0,a0
L10b6
	clr.l	(a0)+
	subq.l	#1,d1
	bne.s	L10b6
L10bc
	tst.l	d0
	rts
_allocate
	moveq	#-8,d1
	addq.l	#7,d0
	and.l	d1,d0
	beq.s	L10f2
	lea	(a0),a1
L10ca
	move.l	(a1),d1
	beq.s	L10f0
	exg	d1,a1
	cmp.l	4(a1),d0
	bhi.s	L10ca
	sub.l	d0,4(a1)
	beq.s	L10ea
	move.l	(a1),(0,a1,d0.l)
	move.l	4(a1),(4,a1,d0.l)
	add.l	a1,d0
	bra.s	L10ec
L10ea
	move.l	(a1),d0
L10ec
	exg	d1,a1
	move.l	d0,(a1)
L10f0
	move.l	d1,d0
L10f2
	rts
_freemem
	tst.l	d0
	beq.s	L1174
	movea.l	_fastfree(pc),a0
	IFND	NOMUSIC
	cmpa.l	#589824,a1
	ELSE
	cmpa.l	#438272,a1
	ENDC
	bcc.s	L1108
	movea.l	_chipfree(pc),a0
L1108
	movem.l	a2,-(sp)
	move.l	a1,d1
	andi.b	#-8,d1
	exg	d1,a1
	sub.l	a1,d1
	add.l	d1,d0
	addq.l	#7,d0
	andi.b	#-8,d0
	lea	(a0),a2
	move.l	(a2),d1
	beq.s	L1146
L1124
	cmpa.l	d1,a1
	bls.s	L1130
	movea.l	d1,a2
	move.l	(a2),d1
	bne.s	L1124
	bra.s	L1132
L1130
	beq.s	_fault2
L1132
	moveq	#0,d1
	add.l	a0,d1
	cmp.l	a2,d1
	beq.s	L1146
	move.l	4(a2),d1
	add.l	a2,d1
	cmp.l	a1,d1
	beq.s	L1150
	bhi.s	_fault3
L1146
	move.l	(a2),(a1)
	move.l	a1,(a2)
	move.l	d0,4(a1)
	bra.s	L1156
L1150
	add.l	d0,4(a2)
	movea.l	a2,a1
L1156
	tst.l	(a1)
	beq.s	L1172
	move.l	4(a1),d1
	add.l	a1,d1
	cmp.l	(a1),d1
	bhi.s	_fault3
	bne.s	L1172
	movea.l	(a1),a2
	move.l	(a2),(a1)
	move.l	4(a2),d1
	add.l	d1,4(a1)
L1172
	movea.l	(sp)+,a2
L1174
	rts
	tst.w	(-$100).w
_fault2
	tst.w	(-$200).w
_fault3
	tst.w	(-$300).w
	illegal
_nochip
	pea	_nochipmsg(pc)
	bra.s	L118e
_nofast
	pea	_nofastmsg(pc)
L118e
	pea	($2b).w
	bra.w	_abort
_nochipmsg
	dc.b	"Slave has not enough chip memory!",0
_nofastmsg
	dc.b	"Slave has not enough fast memory!",0
_ctrltags
	dc.l	$88000000
_attnflags
	dc.l	$0
	dc.l	$88000002
_monitor
	dc.l	$0
	dc.l	$88000008
_custom2
	dc.l	$0
	dc.l	$88000009
_custom3
	dc.l	$0
	IFND	NOMUSIC
	dc.l	$8800000a
_custom4
	dc.l	$0
	ENDC
	dc.l	$0
_resload
	dc.l	$0
	IFND	NOMUSIC
	dc.w	$0
	ENDC

	IFND	ORIGINAL
	CNOP	0,4
	INCLUDE	palette.s
	INCLUDE	display.s
	ENDC
