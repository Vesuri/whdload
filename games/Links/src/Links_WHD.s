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
;		  self-modifying code in v1.50, v1.53's span loops without it),
;		  v1.53's course picture to the screen 16 pixels a word instead
;		  of a pixel at a time on 68020+, code and variables of the chip
;		  memory hunks moved to fast memory, the intro's pictures no
;		  longer damaged by its music nor its credits overlapping,
;		  samples centred and scaled
;		  to 8 bits, and channels stopped on silence: no pops
;		  around the sounds and the music

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

; _copyscr's tables and row buffer, on a 68020 or later; without them the game's own copy runs
	btst	#AFB_68020,AttnFlags+1(a6)
	beq.b	.noc2p
	move.l	#C2P_SIZE,d0
	moveq	#MEMF_PUBLIC,d1
	jsr	_LVOAllocMem(a6)
	lea	C2PBUF(pc),a0
	move.l	d0,(a0)
	beq.b	.noc2p
	move.l	d0,a0
	bsr.w	_c2pinit
.noc2p	move.l	DOSbase(pc),a6

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
C2PBUF	dc.l	0			; _copyscr's tables and row buffer (C2P_SIZE), or 0

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
;
; The music stops channels 0 and 1 mid-sample when the intro is clicked away (hunk 8 $f6),
; and on the interrupt that reloads the last sample when it ends (hunk 8 $ba). Paula holds
; its last output byte, at volume 64 on channel 1: a DC level, and a pop when the game's
; first sample starts. _audiooff ends both on a zero word.
PLTITLE	PL_START
	PL_PS	$7a4,_creditpace	; hunk 0 $7a4: the credits' scroll loop, 5 fields a turn
	PL_S	$2614,12		; hunk 8 $78
	PL_PS	$2656,_audioend		; hunk 8 $ba: volume, DMA and interrupt off
	PL_S	$265c,$d2-$c0
	PL_PS	$2692,_audiooff		; hunk 8 $f6: DMA off
	PL_NOP	$2698,2
	PL_PS	$259c,_introstart	; hunk 8 $0: the music's start
	PL_NOP	$25a2,4
	PL_PS	$25e8,_sndprep		; hunk 8 $4c: the sample's length
	PL_NOP	$25ee,4
	PL_END

; The end of the music, in its audio interrupt (a0: the -1 that ends the list): the list
; pointer (hunk 8 $128) stays on the -1, so a later interrupt stops again instead of reading
; past the list.
_audioend
	move.l	(sp),a0			; hunk 8 $c0
	subq.l	#2,$128-$c0(a0)

; Channels 0 and 1 off: with DMA off and their interrupt requests clear, Paula plays the word
; written to AUDxDAT after the current one, sets the request and idles on its last byte, 0.
; Channel 0's interrupt goes off first: the request the current word's end raises would
; otherwise start the music's next sample, with DMA, before the click path disables the
; interrupt (hunk 8 $fe).
_audiooff
	move.w	#$80,$dff09a		; INTENA
	move.w	#3,$dff096		; DMACON
	move.w	#$180,$dff09c		; INTREQ
	move.w	#0,$dff0aa		; AUD0DAT
	move.w	#0,$dff0ba		; AUD1DAT
	rts

; The sounds the game loads at its start (hunk 44 $814, into their own buffer) are centred as
; they load, in the walk that enters them in the sample table (a0 the header). The others are
; loaded just before they play, so the player centres them (and a cached one is marked).
_sndwalk
	move.l	d0,-(sp)
	bsr.b	_sndprep
	move.l	(sp)+,d0
	move.b	8(a0),d2
	asl.w	#8,d2
	rts

; The samples (headers "STEVEH", length at 7-8 little-endian, data from 32) hold 0-69, silence
; at 35, as signed bytes: every sound sat on a level of +35, which each start and end of a
; sample stepped to and from. Some end in zero bytes, and the last sample of each group the game
; loads runs on into the next group's header, which is loaded over its last 32 bytes.
;
; a0: a sample's header. Returns its length in d0.w, cut at a header in its last 40 bytes. On
; the first call it centres the data on 0 (but the trailing zero bytes, which stay 0) and
; marks the header ("STEVEh"). Keeps every other register and d0's upper word (the game's
; player keeps the channel there). The data goes through _sndgame: 35 to 0, scaled by 3.5 to
; -123..119, about the full 8 bits, 11 dB louder at the same volume. _sndtab takes the
; table in a3 (the intro's).
_sndprep
	move.l	a3,-(sp)
	lea	_sndgame(pc),a3
	bsr.b	_sndtab
	move.l	(sp)+,a3
	rts

_sndtab
	movem.l	d1-d3/a1-a2,-(sp)
	moveq	#0,d1
	move.b	8(a0),d1
	lsl.w	#8,d1
	move.b	7(a0),d1		; the length
	lea	32(a0),a1		; the data
	move.l	d1,d3
	subq.l	#4,d3			; the last offset a header can start at
	move.l	d1,d2
	sub.l	#40,d2
	bcc.b	.from
	moveq	#0,d2
.from	lea	(a1,d2.l),a2
.scan	cmp.l	d3,d2
	bgt.b	.conv
	cmp.b	#"S",(a2)+
	bne.b	.next
	cmp.b	#"T",(a2)
	bne.b	.next
	cmp.b	#"E",1(a2)
	bne.b	.next
	cmp.b	#"V",2(a2)
	bne.b	.next
	move.l	d2,d1			; the length up to that header
	bra.b	.conv
.next	addq.l	#1,d2
	bra.b	.scan
.conv	cmp.b	#"H",6(a0)
	bne.b	.done
	move.b	#"h",6(a0)
	lea	(a1,d1.l),a2
.zero	cmp.l	a1,a2			; skip the trailing zero bytes
	bls.b	.done
	tst.b	-(a2)
	beq.b	.zero
	addq.l	#1,a2
	moveq	#0,d2
.centre	move.b	(a1),d2
	move.b	(a3,d2.w),(a1)+
	cmp.l	a2,a1
	blo.b	.centre
.done	move.w	d1,d0
	movem.l	(sp)+,d1-d3/a1-a2
	rts

; The credits' scroll (hunk 0 $7a0) turns its loop 98 times as fast as the machine runs, while
; the credits in it change on the field timer hunk 3 $120 (step 0 the first, 1 blank, 2 the
; second, 3 blank). After the loop hunk 0 $726 draws COPYRIGHT straight onto the screen: on a
; 68000 the loop takes 490 fields, 5 a turn, and ends in step 3; on the a1200-030 with CACHE
; it took 388 and ended in step 2, under the second credit. At the loop's top (tst.b of the
; click flag, hunk 3 $11d) this waits until 5 fields have passed since the last turn, on the
; VBL's fourth counter (hunk 3 $124, unused), and keeps the flag test.
_creditpace
	move.l	a0,-(sp)
	move.l	4(sp),a0		; hunk 0 $7aa
	move.l	$7ae-$7aa(a0),a0	; hunk 3 $120 (tst.w's operand)
.wait	tst.b	$11d-$120(a0)		; clicked: no wait
	bne.b	.out
	tst.w	$124-$120(a0)
	bne.b	.wait
	move.w	#5,$124-$120(a0)
.out	tst.b	$11d-$120(a0)
	move.l	(sp)+,a0		; keeps the flags
	rts

; The intro's music start (hunk 8 $0, lea $12c(pc),a0 and move.l a0,$128): first centres every
; sample of the table hunk 0 $b1c built (its address is hunk 8 $e's operand), following the
; headers as that routine does, so that the audio interrupt does not have to. The music's
; samples average 29.5, not 35 (they hold no silence), so _sndintro centres them on 30 and
; scales them by 3.25, to -98..126.
_introstart
	movem.l	d0-d1/a1-a3,-(sp)
	move.l	20(sp),a1		; hunk 8 $6
	lea	_sndintro(pc),a3
	move.l	$e-6(a1),a2		; hunk 0 $b4c
	move.l	(a2),d0
	beq.b	.end
	move.l	d0,a0
.walk	bsr.w	_sndtab
	moveq	#0,d1
	move.b	8(a0),d1
	lsl.w	#8,d1
	move.b	7(a0),d1
	lea	32(a0,d1.l),a0
	cmp.b	#"S",(a0)
	bne.b	.end
	cmp.b	#"T",1(a0)
	beq.b	.walk
.end	lea	$12c-6(a1),a0
	move.l	a0,$128-6(a1)
	movem.l	(sp)+,d0-d1/a1-a3
	rts

; SNDTAB centre,num,shift: 256 bytes, byte n to (n - centre) * num / 2^shift, rounded down and
; held to -128..127.
SNDTAB	MACRO
SNDN	SET	0
	REPT	256
SNDV	SET	(SNDN-\1)*\2
	IFLT	SNDV
SNDV	SET	-((-SNDV+(1<<\3)-1)>>\3)
	ELSE
SNDV	SET	SNDV>>\3
	ENDIF
	IFGT	SNDV-127
SNDV	SET	127
	ENDIF
	IFLT	SNDV+128
SNDV	SET	-128
	ENDIF
	dc.b	SNDV
SNDN	SET	SNDN+1
	ENDR
	ENDM

_sndgame	SNDTAB	35,7,1
_sndintro	SNDTAB	30,13,2

PLGAME150
	PL_START
	PL_SA	$2da,$2e8		; skip cache clear
	PL_PS	$1546c,getFIB		; fix course disk support
	PL_PS	$15476,getFIB2		; as above
	PL_B	$2a879,-3		; hunk 44 $a61, sample end count
	PL_B	$2a87f,-3		; hunk 44 $a67
	PL_PS	$2a834,_sndprep		; hunk 44 $a1c: the sample's length
	PL_NOP	$2a83a,4
	PL_PS	$2a678,_sndwalk		; hunk 44 $860: the walk of the sounds loaded at the start
	PL_END

PLGAME153
	PL_START
	PL_SA	$2e4,$2f2		; skip cache clear
	PL_PS	$15478,getFIB		; fix course disk support
	PL_PS	$15482,getFIB2		; as above
	PL_B	$2aa8b,-3		; hunk 44 $a6b, sample end count
	PL_B	$2aa91,-3		; hunk 44 $a71
	PL_PS	$2aa46,_sndprep		; hunk 44 $a26: the sample's length
	PL_NOP	$2aa4c,4
	PL_PS	$2a87e,_sndwalk		; hunk 44 $85e: the walk of the sounds loaded at the start
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
	PL_PA	$1446e,_sp1+$5e2-$5e2	; hunk 12 $502-$5cc: the span loop's opcodes and
	PL_PA	$14498,_sp1+$5e2-$5e2	; displacements are written to _sp1, not into the loop
	PL_PA	$14476,_sp1+$5e6-$5e2
	PL_PA	$144a0,_sp1+$5e6-$5e2
	PL_PA	$1447e,_sp1+$5ea-$5e2
	PL_PA	$144a8,_sp1+$5ea-$5e2
	PL_PA	$14486,_sp1+$5ee-$5e2
	PL_PA	$144b0,_sp1+$5ee-$5e2
	PL_PA	$1448e,_sp1+$5f0-$5e2
	PL_PA	$144b8,_sp1+$5f0-$5e2
	PL_PA	$144ce,_sp1+$5fc-$5e2
	PL_PA	$144d8,_sp1+$5fc-$5e2
	PL_PA	$144fa,_sp1+$5fe-$5e2
	PL_PA	$14504,_sp1+$5fe-$5e2
	PL_PA	$1452a,_sp1+$600-$5e2
	PL_PA	$14534,_sp1+$600-$5e2
	PL_PS	$14544,_span1		; hunk 12 $5dc: the loop $5e2-$60a, from _sp1
	PL_PA	$14666,_sp2		; hunk 12 $6fa-$738: bclr/bset #6 on _sp2 and _sp2+1,
	PL_PA	$14670,_sp2		; not on the opcodes at $78a and $790
	PL_PA	$14694,_sp2+1
	PL_PA	$1469e,_sp2+1
	PL_PS	$146b0,_span2		; hunk 12 $748: the loop $74e-$796, signs from _sp2
	PL_PS	$1597c,_flushcache	; hunk 14 $48: four immediates
	PL_PS	$14a5a,_copyscr		; hunk 12 $af2: the picture to the screen
	PL_END

; v1.53's span loop (hunk 12 $5e2-$60a), after the set-up at $502-$5cc chose its first
; instruction (nop, or addq.w #1,d0), the displacement of its first move (0 or 6; the next
; two are 2 and 4 on), and add or sub (opcode bit 6) for its adda #12,a1 and the three steps
; d4-d6. The same with the signs on registers; returns to $60c. The last instruction that
; sets flags is the loop's subq, as in the original.
_span1	movem.l	d4-d7/a0/a2,-(a7)
	move.l	6*4(a7),a2
	lea	$60c-$5e2(a2),a2
	move.l	a2,6*4(a7)		; return to hunk 12 $60c
	lea	_sp1(pc),a0
	cmp.w	#$4e71,(a0)		; $5e2: nop or addq.w #1,d0
	beq.b	.nop
	addq.w	#1,d0
.nop	move.w	$5e6-$5e2(a0),d7
	lea	(a1,d7.w),a2		; a2: a1 + the first displacement
	moveq	#12,d7
	btst	#6,$5f0-$5e2(a0)	; adda.l ($d3fc) or suba.l ($93fc) #12,a1
	bne.b	.a
	neg.l	d7
.a	btst	#6,$5fc-$5e2(a0)	; add.l ($d084) or sub.l ($9084) d4,d0
	bne.b	.b
	neg.l	d4
.b	btst	#6,$5fe-$5e2(a0)	; d5,d1
	bne.b	.c
	neg.l	d5
.c	btst	#6,$600-$5e2(a0)	; d6,d2
	bne.b	.loop
	neg.l	d6
.loop	move.w	d0,(a2)
	move.w	d1,2(a2)
	move.w	d2,4(a2)
	add.l	d7,a2
	add.l	d7,a1
	swap	d0
	swap	d1
	swap	d2
	add.l	d4,d0
	add.l	d5,d1
	add.l	d6,d2
	swap	d0
	swap	d1
	swap	d2
	subq.w	#1,d3
	bne.b	.loop
	movem.l	(a7)+,d4-d7/a0/a2
	rts

; v1.53's pixel loop (hunk 12 $74e-$796), its two steps added or subtracted as the set-up at
; $6fa-$738 marked bit 6 of _sp2 (d6) and _sp2+1 (d7). Returns to $798 with the flags of
; the loop's last subq.
_span2	movem.l	d6-d7/a2,-(a7)
	move.l	3*4(a7),a2		; hunk 12 $74e
	btst	#6,_sp2(pc)		; add.l ($d286) or sub.l ($9286) d6,d1
	bne.b	.a
	neg.l	d6
.a	btst	#6,_sp2+1(pc)		; add.l ($d087) or sub.l ($9087) d7,d0
	bne.b	.b
	neg.l	d7
.b	move.l	a4,d5
	sub.l	d3,d3
	move.w	(a0),d3
	add.l	d3,d5
	sub.l	d0,d0
	move.w	4(a0),d0
	add.w	$bda-$74e(a2),d0
	sub.l	d1,d1
	move.w	2(a0),d1
	lea	$798-$74e(a2),a2
	move.l	a2,3*4(a7)		; return to hunk 12 $798
.loop	move.l	d5,d3
	add.l	d3,d3
	cmp.w	(a1,d3.l),d1
	bcc.b	.next
	move.w	d1,(a1,d3.l)
	move.b	d0,(a5,d5.l)
	asl.w	#2,d0
	move.b	(a6,d0.w),(a3,d5.l)
	lsr.w	#2,d0
.next	subq.w	#1,d2
	beq.b	.done
	swap	d1
	add.l	d6,d1
	swap	d1
	swap	d0
	add.l	d7,d0
	swap	d0
	addq.l	#1,d5
	bra.b	.loop
.done	movem.l	(a7)+,d6-d7/a2
	rts

_sp1	ds.b	$602-$5e2		; hunk 12 $5e2-$601 as the set-up writes it
_sp2	dc.b	$40,$40			; bit 6: hunk 12 $78a and $790 add (set) or subtract
	CNOP	0,4

; v1.53 hunk 12 $af2-$ba4 turns the rendered picture (a byte a pixel, 320 x 160) into the
; screen's six planes one pixel at a time: each pixel's colour comes from its byte, its
; region and a dither step, and a jsr to one of hunk 4's 64 routines sets or clears its bit
; in every plane of the visible screen (6 read-modify-writes of chip memory a pixel). The
; same colours go to a row buffer, and each row goes to the planes 16 pixels a word.
; d0: the first row. Without C2PBUF the game's own code runs.
C2P_T01	= 0				; colour -> plane 0 bit 16, plane 1 bit 0
C2P_T23	= 1024
C2P_T45	= 2048
C2P_ROW	= 3072
C2P_SIZE = 3072+320

	MC68020				; _copyscr runs on a 68020 or later (PLCACHE153)
_copyscr
	move.l	(a7)+,a0		; hunk 12 $af8
	move.l	C2PBUF(pc),d1
	bne.b	.c2p
	move.l	$ba6-$af8(a0),a1	; the instruction replaced: movea.l (hunk 12 $ba6),a1
	jmp	(a0)
.c2p	move.l	d1,a5
	move.l	$ba6-$af8(a0),a1	; the same registers as the original: a1 the depth map
	move.l	$afa-$af8(a0),a2	; (hunk 12 $af8: movea.l abs,a2) the screen, plane 1
	move.l	(a2),a2
	move.l	$b00-$af8(a0),a3	; ($afe: lea abs,a3) colour and dither table
	move.l	$b06-$af8(a0),a4	; ($b04) the picture
	move.l	(a4),a4
	move.l	$b0c-$af8(a0),a6	; ($b0a) its regions
	move.l	(a6),a6
	moveq	#0,d7
	move.w	d0,d7
	lsl.l	#6,d7
	move.l	d7,d1
	lsl.l	#2,d1
	add.l	d1,d7			; d7 = the first row x 320
.row	moveq	#0,d5			; hunk 12 $b1e, as the original
	moveq	#0,d6
	lea	C2P_ROW(a5),a0
.px	moveq	#0,d0
	move.b	(a4,d7.l),d0
	bmi.b	.neg
	cmp.b	(a6,d7.l),d6
	beq.b	.same
	moveq	#0,d4
	move.b	(a6,d7.l),d6
.same	lsl.w	#2,d0
	add.w	d4,d0
	move.b	(a3,d0.w),d0
	addq.w	#1,d4
	cmp.b	#4,d4
	blt.b	.put
	moveq	#1,d4
	bra.b	.put
.neg	moveq	#1,d4
	neg.b	d0
	cmp.b	(a6,d7.l),d6
	beq.b	.put
	move.l	d7,d2
	add.l	d2,d2
	cmp.w	#-1,(a1,d2.l)
	bne.b	.take
	cmp.w	#-1,-2(a1,d2.l)
	beq.b	.put
.take	move.b	(a6,d7.l),d6
	move.b	d6,d0
.put	move.b	d0,(a0)+		; the original's jsr to hunk 4 for colour d0
	addq.l	#1,d7
	addq.w	#1,d5
	cmp.w	#320,d5
	bmi.b	.px
	movem.l	d4/d7/a1/a3-a4/a6,-(a7)
	sub.l	#320,d7
	lsr.l	#3,d7
	lea	(a2,d7.l),a1		; the row in plane 1
	lea	C2P_ROW(a5),a0
	lea	C2P_T01(a5),a3
	lea	C2P_T23(a5),a4
	lea	C2P_T45(a5),a6
	moveq	#0,d0
	moveq	#320/16-1,d4
.word	moveq	#0,d1
	moveq	#0,d2
	moveq	#0,d3
	moveq	#16-1,d5
.bit	move.b	(a0)+,d0
	add.l	d1,d1
	or.l	(a3,d0.w*4),d1
	add.l	d2,d2
	or.l	(a4,d0.w*4),d2
	add.l	d3,d3
	or.l	(a6,d0.w*4),d3
	dbf	d5,.bit
	move.w	d1,(a1)			; plane 1
	swap	d1
	move.w	d1,-8000(a1)		; plane 0
	move.w	d2,16000(a1)		; plane 3
	swap	d2
	move.w	d2,8000(a1)		; plane 2
	move.w	d3,32000(a1)		; plane 5
	swap	d3
	move.w	d3,24000(a1)		; plane 4
	addq.l	#2,a1
	dbf	d4,.word
	movem.l	(a7)+,d4/d7/a1/a3-a4/a6
	cmp.l	#51200,d7		; hunk 12 $b9a
	blo.w	.row
	rts
	MC68000

; a0: C2PBUF. Its three tables: for each byte (its low 6 bits the colour) planes 0 and 1,
; 2 and 3, 4 and 5 as bits 16 and 0
_c2pinit
	movem.l	d2-d3,-(a7)
	moveq	#0,d3			; the first plane: 0, 2, 4
.tab	moveq	#0,d0
.t	move.l	d0,d1
	lsr.w	d3,d1
	moveq	#0,d2
	lsr.w	#1,d1
	bcc.b	.1
	bset	#16,d2
.1	lsr.w	#1,d1
	bcc.b	.2
	bset	#0,d2
.2	move.l	d2,(a0)+
	addq.w	#1,d0
	cmp.w	#256,d0
	bne.b	.t
	addq.w	#2,d3
	cmp.w	#6,d3
	bne.b	.tab
	movem.l	(a7)+,d2-d3
	rts

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

