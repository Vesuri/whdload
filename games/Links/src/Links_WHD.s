***************************************************************************
*             /                                                           *
*       _____.__ _                                         .___.          *
*      /    /_____________.  _________.__________.________ |   |________  *
*  ___/____      /    ____|_/         |         /|        \|   ._      /  *
*  \     \/      \    \     \    /    |    :___/¯|    \    \   |/     /   *
*   \_____________\___/_____/___/_____|____|     |____|\_____________/    *
*     -========================/===========|______\================-      *
*                                                                         *
*   .---.----(*( LINKS - THE CHALLENGE OF GOLF WHDLOAD SLAVE )*)---.---.  *
*   `-./                                                            \.-'  *
*                                                                         *
*                         (c)oded by StingRay                             *
*                         --------------------                            *
*                              April 2013                                 *
*                                                                         *
*                                                                         *
***************************************************************************

***********************************
*** History			***
***********************************

; 25-Nov-2026	- 2.0b by Vesuri: the renderer's self-modifying code made safe
;		  for the caches on 68020+ (flushes, a per-pixel change without
;		  self-modifying code in v1.50), code and variables of the chip
;		  memory hunks moved to fast memory, the intro's pictures no
;		  longer damaged by its music, no pops around the game's samples
;		  on machines with fast memory

; 28-Apr-2013	- course disk bug fixed, game destroyed the FIB while
;		  trying to read the course name so only 1 coourse
;		  would be displayed in the requester, lame!

; 13-Apr-2013	- work started


	;INCDIR	SOURCES:Include/	; vasm: the build passes the include paths
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	;INCLUDE	lvo/dos.i

; absolute skip
PL_SA	MACRO
	PL_S	\1,\2-(\1)
	ENDM

MC68020	MACRO
	ENDM

;============================================================================

CHIPMEMSIZE	= 524288
FASTMEMSIZE	= 524288*2
NUMDRIVES	= 1
WPDRIVES	= %0000

BLACKSCREEN
;BOOTBLOCK
BOOTDOS
;BOOTEARLY
;CBDOSLOADSEG
;CBDOSREAD
CACHE
;DEBUG		; vasm: the shipped slave was built without it (no debug strings)
;DISKSONBOOT
;DOSASSIGN
FONTHEIGHT	= 8
HDINIT
HRTMON
;INITAGA
;INIT_AUDIO
;INIT_GADTOOLS
;INIT_LOWLEVEL
;INIT_MATHFFP
IOCACHE		= 8192
;JOYPADEMU
;MEMFREE	= $200
;NEEDFPU
NO68020
POINTERTICKS	= 1
;PROMOTE_DISPLAY
STACKSIZE	= 6000
;TRDCHANGEDISK

;============================================================================

slv_Version	= 17
slv_Flags	= WHDLF_NoError|WHDLF_Examine
slv_keyexit	= $59	; F10

;============================================================================

	INCLUDE	whdload/kick13.s	; vasm: was Sources:whdload/kick13.s
	INCLUDE	dos/doshunks.i

;============================================================================


slv_CurrentDir	IFD	DEBUG
		dc.b	"SOURCES:WHD_Slaves/Links/data",0
		ELSE
		dc.b	"data",0
		ENDIF

slv_name	dc.b	"Links - The Challenge of Golf",0
slv_copy	dc.b	"1992 Access",0
slv_info	dc.b	"installed by StingRay/[S]carab^Scoopex",10
		dc.b	"Version 2.0b by Vesuri",10
		IFD	DEBUG
		dc.b	"DEBUG!!! "
		ENDC
		dc.b	"Version 2.0b (25.11.2026)",0

slv_config	dc.b	"C1:B:Skip Intro"
		dc.b	0
		dc.b	"$VER: Links.slave 2.0b (25.11.2026)",0

		CNOP	0,4
	IFD BOOTDOS

_bootdos
	lea	_dosname(pc),a1
	move.l	$4.w,a6
	jsr	_LVOOldOpenLibrary(a6)
	lea	DOSbase(pc),a0
	move.l	d0,(a0)
	move.l	d0,a6

	move.l	_resload(pc),a2
	lea	TAGLIST(pc),a0
	jsr	resload_Control(a2)

; the chip memory word the game's samples end in (PLCHIP); without it those patches are skipped
	move.l	$4.w,a6
	moveq	#8,d0
	move.l	#MEMF_CHIP|MEMF_CLEAR,d1
	jsr	_LVOAllocMem(a6)
	lea	SILENT(pc),a0
	move.l	d0,(a0)
	move.l	DOSbase(pc),a6

; load intro
	move.l	NOINTRO(pc),d0
	bne.b	.skipintro
	moveq	#0,d0
	moveq	#4,d1
	lea	.title(pc),a0
	lea	PT_TITLE(pc),a1
	bsr.b	.LoadAndPatch
	bsr.b	.run
.skipintro

; load game
.dogame	move.w	#$12e,d0
	move.w	#$146-$12e,d1
	lea	.game(pc),a0
	lea	PT_GAME(pc),a1
.go	bsr.b	.LoadAndPatch
	bsr.b	.run
	bra.w	QUIT

.run	move.l	d7,a1
	add.l	a1,a1
	add.l	a1,a1
	movem.l	d7/a6,-(a7)
	lea	.cmd(pc),a0
	moveq	#.cmdlen,d0
	jsr	4(a1)
	movem.l	(a7)+,d7/a6
	move.l	d7,d1
	jmp	_LVOUnLoadSeg(a6)

; d0.w: start offset for version check
; d1.w: length for version check
; a0.l: file name
; a1.l: patch table
; a6.l: dos base
; ---
; d7: segment

.LoadAndPatch
	move.w	d0,d3
	moveq	#0,d4
	move.w	d1,d4

	move.l	a0,d6
	move.l	a1,a5
	move.l	a0,d1
	jsr	_LVOLoadSeg(a6)
	move.l	d0,d7
	beq.w	.error

	move.l	d7,a0
	add.l	a0,a0
	add.l	a0,a0

	lea	4(a0,d3.w),a0
	move.l	d4,d0
	move.l	_resload(pc),a2
	jsr	resload_CRC16(a2)
	move.w	d0,d2

; d0: checksum
	move.l	a5,a0
.find	move.w	(a0)+,d0
	beq.b	.wrongver
	cmpi.w	#-1,d0			; cmpi: the shipped encoding
	beq.b	.out
	cmpi.w	#-2,d0			; don't care about CRC (cmpi: the shipped encoding)
	beq.b	.found
	cmp.w	d0,d2
	beq.b	.found
	addq.w	#PT_SIZE-2,a0
	bra.b	.find

; unsupported/unknown version
.wrongver
	pea	(TDREASON_WRONGVER).w
	bra.b	EXIT


.found	move.l	a0,a4			; the version's offsets: patches, cache fixes, moves
	move.l	a5,a0
	add.w	(a4),a0
	bsr.b	.patch
	move.w	2(a4),d0		; the cache fixes, on a 68020 or later
	beq.b	.nocache
	move.l	$4.w,a0
	btst	#AFB_68020,AttnFlags+1(a0)
	beq.b	.nocache
	move.l	a5,a0
	add.w	d0,a0
	bsr.b	.patch
.nocache
	move.w	4(a4),d0		; the patches that need the chip memory word
	beq.b	.nochip
	lea	SILENT(pc),a0
	tst.l	(a0)
	beq.b	.nochip
	move.l	a5,a0
	add.w	d0,a0
	bsr.b	.patch
.nochip
	move.l	a5,a1			; the code to move out of chip memory
	add.w	6(a4),a1
	move.l	d6,a0
	bra.w	MoveCode

.patch	move.l	d7,a1
	move.l	_resload(pc),a2
	jmp	resload_PatchSeg(a2)
.out	rts

.error	jsr	_LVOIoErr(a6)
	move.l	d6,-(a7)
	move.l	d0,-(a7)
	pea	(TDREASON_DOSREAD).w
	bra.b	EXIT


.cmd	dc.b	0,10,0			; fake command line (vasm: was "",10,0; the shipped slave has the 0)
.cmdlen	= *-.cmd
.title	dc.b	"title",0
.game	dc.b	"golf",0
	CNOP	0,4


QUIT	pea	(TDREASON_OK).w
EXIT	move.l	_resload(pc),a2
	jmp	resload_Abort(a2)

DOSbase	dc.l	0
SILENT	dc.l	0			; 8 cleared bytes of chip memory, or 0

; format: checksum, offset to patch list, offset to the patch list for a 68020 or later
; (0: none), offset to the patch list that needs SILENT (0: none), offset to the MoveCode
; table
PT_SIZE	= 10
PT_TITLE
	dc.w	-2,PLTITLE-PT_TITLE,0,0,MVTITLE-PT_TITLE	; SPS 2010+SPS2481 (1.50/1.53)
	dc.w	0			; end of tab


; format: as PT_TITLE
PT_GAME	dc.w	$e70a,PLGAME150-PT_GAME,PLCACHE150-PT_GAME,PLCHIP150-PT_GAME,MVGAME150-PT_GAME	; SPS 2010 (v1.50)
	dc.w	$371d,PLGAME153-PT_GAME,PLCACHE153-PT_GAME,PLCHIP153-PT_GAME,MVGAME153-PT_GAME	; SPS 2481 (v1.53)
	dc.w	0			; end of tab


; The intro's music routine (hunk 8 $74) marks two channel counters with move.b #-2,
; (0,a2,d0.w) and (1,a2,d0.w), but d0 holds the sample's length there (the game's own copy of
; the routine has the channel), so each sample start wrote two bytes up to 64 KB past the hunk:
; under WHDLoad into the buffer the pictures are unpacked from, which damaged the picture
; being unpacked. Nothing reads the counters; the writes are skipped.
PLTITLE	PL_START
	PL_S	$2614,12		; hunk 8 $78
	PL_END

PLGAME150
	PL_START
	PL_SA	$2da,$2e8		; skip cache clear
	PL_PS	$1546c,getFIB		; fix course disk support
	PL_PS	$15476,getFIB2		; as above
	PL_B	$2a879,-3		; hunk 44 $a61, sample end count
	PL_B	$2a87f,-3		; hunk 44 $a67
	PL_END

PLGAME153
	PL_START
	PL_SA	$2e4,$2f2		; skip cache clear
	PL_PS	$15478,getFIB		; fix course disk support
	PL_PS	$15482,getFIB2		; as above
	PL_B	$2aa8b,-3		; hunk 44 $a6b, sample end count
	PL_B	$2aa91,-3		; hunk 44 $a71
	PL_END

; The sample player (hunk 44 $9f4, v1.53 offsets) counts the first channel's audio
; interrupts from -2 and switches the pair off on the second (hunk 44 $af8 and on). That one
; comes when Paula has fetched the sample's last word, before the silent loop plays, so Paula
; holds its last output byte, and the second channel's volume is never cleared: a DC offset,
; with a pop when the sample ends and another when the next one sets the volume. Counting
; from -3 lets one silent block play first.
;
; After a sample the game loops its channels on two zero words in hunk 44 ($123c v1.53,
; $1236 v1.50), until the next audio interrupt switches them off. Hunk 44 is not a chip memory
; hunk, so from fast memory Paula played whatever chip memory was at that address and the
; channel kept the last of it: a pop at the end of the sample, and another when the next one
; set the volume. The loop now plays SILENT.
PLCHIP150
	PL_START
	PL_PS	$2a8a4,_silence		; hunk 44 $a8c
	PL_S	$2a8aa,$1c-6
	PL_END

PLCHIP153
	PL_START
	PL_PS	$2aab6,_silence		; hunk 44 $a96
	PL_S	$2aabc,$1c-6
	PL_END

; a1: the first channel's registers
_silence
	move.w	#2,4(a1)		; AUDxLEN, two words
	move.l	SILENT(pc),(a1)		; AUDxLC
	move.w	#2,$14(a1)
	move.l	SILENT(pc),$10(a1)
	rts

; The renderer modifies its own code and then jumps to the next instruction, which on a
; 68000 only empties the prefetch. On a 68020 or later each such jmp becomes a call that
; flushes the caches and returns to the next instruction (kick13.s' _flushcache:
; resload_FlushCache keeps every register; the code after each sets X before it is read).
; v1.50 also changes a displacement byte for every pixel (move.b d4,x; jmp; move.b
; (0,a6,d0.w),d6, d4 0-3); that becomes adda.w d4,a6; move.b (0,a6,d0.w),d6;
; suba.w d4,a6; bra.s to the next instruction, with no flush.
PLCACHE150
	PL_START
	PL_PS	$14520,_flushcache	; hunk 12 $5d4: the span loop's opcodes and offsets
	PL_PS	$14692,_flushcache	; hunk 12 $746: an opcode and two immediates
	PL_DATA	$146dc,10		; hunk 12 $790
	dc.w	$dcc4,$1c36,$0000,$9cc4,$6006
	PL_DATA	$14784,10		; hunk 12 $838
	dc.w	$dcc4,$1c36,$0000,$9cc4,$6006
	PL_PS	$15964,_flushcache	; hunk 14 $3c: three immediates
	PL_END

PLCACHE153
	PL_START
	PL_PS	$14544,_flushcache	; hunk 12 $5dc: the span loop's opcodes and offsets
	PL_PS	$146b0,_flushcache	; hunk 12 $748: two opcodes
	PL_PS	$1597c,_flushcache	; hunk 14 $48: four immediates
	PL_END

; MoveCode tables: hunk, split: the hunk's bytes below split (its code and variables) move
; to fast memory, the rest (sprites, copper list) stays in chip memory; -1. Then hunk,
; offset of each lea d16(pc),An below the split that addresses the rest; -1.
MVTITLE	dc.w	3,$126			; interrupt code; pointer table and copper data
	dc.w	-1
	dc.w	-1

MVGAME150
	dc.w	2,$374			; code; sprites
	dc.w	20,$55e			; interrupt code, variables; copper list
	dc.w	24,$144			; the memory check
	dc.w	-1
	dc.w	2,$19e,2,$20e,20,$21e,20,$32e,20,$342,20,$34e
	dc.w	-1

MVGAME153
	dc.w	2,$374
	dc.w	20,$5b4
	dc.w	24,$144
	dc.w	-1
	dc.w	2,$19e,2,$20e,20,$228,20,$384,20,$398,20,$3a4
	dc.w	-1

; MoveCode: copy the code part of a program's chip memory hunks to fast memory and redirect
; every reference to it. The references come from the program file's HUNK_RELOC32 blocks:
; a relocated long that points below a moved hunk's split gets the copy's address (in the
; copy itself when the long lies in a moved part). A lea d16(pc),An in a moved part that
; addresses the hunk's rest becomes movea.l d16(pc),An from a pointer stored after the
; copy. Without the memory for the file or a copy the code stays where it is.
; a0 = file name, a1 = MoveCode table, d7 = segment list (BPTR). Keeps every register.

MV_OLD		= 0			; the hunk's address
MV_NEW		= 4			; the copy's address, 0 when not moved
MV_SPLIT	= 8
MV_SLOT		= 12			; the next free pointer slot after the copy
MV_HUNK		= 16
MV_SIZE		= 20
MV_MAX		= 4			; hunks per program
MV_SLOTS	= 8			; pointer slots per copy
MV_FILE		= MV_SIZE*MV_MAX	; the file in memory
MV_FILESIZE	= MV_FILE+4
MV_FRAME	= MV_FILESIZE+4

MoveCode
	movem.l	d0-a6,-(a7)
	link	a5,#-MV_FRAME
	move.l	a7,a4			; a4 = frame
	move.l	a1,a3			; a3 = table
	move.l	a0,d6			; d6 = file name
	move.l	$4.w,a6

	move.l	a4,a0			; no hunks
	moveq	#MV_FRAME/4-1,d0
.clear	clr.l	(a0)+
	dbf	d0,.clear

	move.l	d6,a0			; the file
	move.l	_resload(pc),a2
	jsr	resload_GetFileSize(a2)
	move.l	d0,MV_FILESIZE(a4)
	beq.w	.done
	moveq	#MEMF_PUBLIC,d1
	jsr	_LVOAllocMem(a6)
	move.l	d0,MV_FILE(a4)
	beq.w	.done
	move.l	d6,a0
	move.l	d0,a1
	move.l	_resload(pc),a2
	jsr	resload_LoadFile(a2)

; the copies
	move.l	a4,a2			; a2 = hunk entry
.copy	move.w	(a3)+,d0
	bmi.b	.copied
	move.w	(a3)+,d1
	move.w	d0,MV_HUNK+2(a2)
	move.w	d1,MV_SPLIT+2(a2)
	bsr.w	.hunkbase
	move.l	a0,MV_OLD(a2)
	move.l	MV_SPLIT(a2),d0
	addq.l	#3,d0
	and.w	#-4,d0
	move.l	d0,d2			; d2 = the copy's size, rounded
	add.l	#MV_SLOTS*4,d0
	move.l	#MEMF_PUBLIC|MEMF_FAST,d1
	jsr	_LVOAllocMem(a6)
	move.l	d0,MV_NEW(a2)
	beq.b	.next
	move.l	d0,a1
	add.l	d0,d2
	move.l	d2,MV_SLOT(a2)
	move.l	MV_OLD(a2),a0
	move.l	MV_SPLIT(a2),d0
	jsr	_LVOCopyMem(a6)
.next	add.w	#MV_SIZE,a2
	bra.b	.copy
.copied

; the references
	move.l	MV_FILE(a4),a2		; a2 = file
	move.l	a2,d3
	add.l	MV_FILESIZE(a4),d3	; d3 = its end
	cmp.l	#HUNK_HEADER,(a2)+
	bne.w	.free
.names	move.l	(a2)+,d0		; resident library names
	beq.b	.names_
	lsl.l	#2,d0
	add.l	d0,a2
	bra.b	.names
.names_	move.l	4(a2),d0		; table size, first, last, the sizes
	move.l	8(a2),d1
	sub.l	d0,d1
	addq.l	#1,d1
	lsl.l	#2,d1
	lea	12(a2,d1.l),a2
	moveq	#0,d4			; d4 = hunk number
	move.l	d7,d5			; d5 = its segment (BPTR)
.block	cmp.l	d3,a2
	bhs.w	.leas
	move.l	(a2)+,d0
	and.l	#$3fffffff,d0
	cmp.w	#HUNK_CODE,d0
	beq.b	.skipn
	cmp.w	#HUNK_DATA,d0
	beq.b	.skipn
	cmp.w	#HUNK_BSS,d0
	beq.b	.skip1
	cmp.w	#HUNK_RELOC32,d0
	beq.b	.reloc
	cmp.w	#HUNK_END,d0
	beq.b	.end
	cmp.w	#HUNK_SYMBOL,d0
	beq.b	.symbol
	cmp.w	#HUNK_DEBUG,d0
	bne.w	.leas			; anything else: stop
.skipn	move.l	(a2)+,d0
	lsl.l	#2,d0
	add.l	d0,a2
	bra.b	.block
.skip1	addq.l	#4,a2
	bra.b	.block
.end	addq.l	#1,d4
	lsl.l	#2,d5
	move.l	d5,a0
	move.l	(a0),d5
	bra.b	.block
.symbol	move.l	(a2)+,d0
	beq.b	.block
	addq.l	#1,d0
	lsl.l	#2,d0
	add.l	d0,a2
	bra.b	.symbol

.reloc	move.l	(a2)+,d2		; d2 = offsets
	beq.b	.block
	move.l	(a2)+,d0		; the target hunk
	bsr.w	.entry
	move.l	a0,a1			; a1 = its entry
	move.l	a1,d0
	beq.b	.skipoffs
	move.l	d4,d0			; this hunk's entry
	bsr.w	.entry
	move.l	d5,d1			; d1 = this hunk
	lsl.l	#2,d1
	addq.l	#4,d1
	move.l	MV_NEW(a1),d6		; d6 = the target's displacement
	sub.l	MV_OLD(a1),d6
.off	move.l	(a2)+,d0
	move.l	a0,-(a7)		; the long: in the copy when this part moved
	beq.b	.inold
	cmp.l	MV_SPLIT(a0),d0
	bhs.b	.inold
	move.l	MV_NEW(a0),a0
	bra.b	.site
.inold	move.l	d1,a0
.site	add.l	d0,a0
	move.l	(a0),d0
	sub.l	MV_OLD(a1),d0
	cmp.l	MV_SPLIT(a1),d0
	bhs.b	.keep
	add.l	d6,(a0)
.keep	move.l	(a7)+,a0
	subq.l	#1,d2
	bne.b	.off
	bra.b	.reloc
.skipoffs
	lsl.l	#2,d2
	add.l	d2,a2
	bra.b	.reloc

; the lea d16(pc),An below a split
.leas	move.w	(a3)+,d0
	bmi.b	.free
	moveq	#0,d1
	move.w	(a3)+,d1
	ext.l	d0
	bsr.b	.entry
	move.l	a0,d0
	beq.b	.leas
	move.l	MV_NEW(a0),a1
	add.l	d1,a1			; a1 = the instruction in the copy
	move.w	(a1),d0
	and.w	#$f1ff,d0
	cmp.w	#$41fa,d0
	bne.b	.leas
	move.l	MV_OLD(a0),d0		; its target in the hunk
	add.l	d1,d0
	addq.l	#2,d0
	move.w	2(a1),a2
	add.l	a2,d0
	move.l	MV_SLOT(a0),a2
	move.l	d0,(a2)
	addq.l	#4,MV_SLOT(a0)
	move.w	(a1),d0			; movea.l d16(pc),An
	and.w	#$0e00,d0
	or.w	#$207a,d0
	move.w	d0,(a1)+
	sub.l	a1,a2
	move.w	a2,(a1)
	bra.b	.leas

.free	move.l	MV_FILE(a4),a1
	move.l	MV_FILESIZE(a4),d0
	jsr	_LVOFreeMem(a6)
	move.l	_resload(pc),a2
	jsr	resload_FlushCache(a2)
.done	unlk	a5
	movem.l	(a7)+,d0-a6
	rts

; d0 = hunk number, d7 = segment list: a0 = the hunk's address
.hunkbase
	move.l	d7,a0
.hb	add.l	a0,a0
	add.l	a0,a0
	subq.w	#1,d0
	bmi.b	.hb_
	move.l	(a0),a0
	bra.b	.hb
.hb_	addq.l	#4,a0
	rts

; d0.l = hunk number: a0 = its entry if it moved, else 0; d0 = a0, flags set
.entry	move.l	d1,-(a7)
	move.l	a4,a0
	moveq	#MV_MAX-1,d1
.en	tst.l	MV_NEW(a0)
	beq.b	.en_
	cmp.l	MV_HUNK(a0),d0
	beq.b	.en__
.en_	add.w	#MV_SIZE,a0
	dbf	d1,.en
	sub.l	a0,a0
.en__	move.l	(a7)+,d1
	move.l	a0,d0
	rts

getFIB	pea	FIB(pc)
	move.l	(a7)+,d2
	rts

getFIB2
	lea	FIB(pc),a0
	rts



	CNOP	0,4
FIB	ds.b	fib_SIZEOF

TAGLIST	dc.l	WHDLTAG_CUSTOM1_GET
NOINTRO	dc.l	0
	dc.l	TAG_END




	ENDC

