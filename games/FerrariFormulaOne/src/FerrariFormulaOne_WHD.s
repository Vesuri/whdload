***************************************************************************
*             /                                                           *
*       _____.__ _                                         .___.          *
*      /    /_____________.  _________.__________.________ |   |________  *
*  ___/____      /    ____|_/         |         /|        \|   ._      /  *
*  \     \/      \    \     \    /    |    :___/¯|    \    \   |/     /   *
*   \_____________\___/_____/___/_____|____|     |____|\_____________/    *
*     -========================/===========|______\================-      *
*                                                                         *
*   .---.----(*(      FERRARI FORMULA ONE WHDLOAD SLAVE     )*)---.---.   *
*   `-./                                                           \.-'   *
*                                                                         *
*                         (c)oded by StingRay                             *
*                         --------------------                            *
*                              March 2013                                 *
*                                                                         *
*                                                                         *
***************************************************************************

***********************************
*** History			***
***********************************

; 07-Aug-2016	- version check is now done using the file length so the
;		  different versions can be detected safely
;		- added support for Irek's version which is a later version
;		  of the game with the lame bugs of the earlier SPS 481
;		  version fixed

; 01-Aug-2016	- found real cause for the crash in race, second screen
;		  ptr was set to illegal value due to using d1 as long
;		  without initialising it before...
;		- fixed another bug when leaving the course, same problem
;		  as above, using d0.l without initialising it before which
;		  caused a completely wrong and illegal blit
;		- CPU dependent delay fixed
;		- timing fixed (can be disabled with CUSTOM1)
;		- this patch is now finally finished!

; 31-Jul-2016	- WHDLF_ClearMem flag used now to avoid access fault
;		- crash in race fixed, there are graphics problems though

; 24-Aug-2014	- protection fully removed

; 25-Mar-2013	- work started
;		- protection removed


	INCDIR	SOURCES:Include/
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i

; absolute skip
PL_SA	MACRO
	PL_S	\1,\2-(\1)
	ENDM

;============================================================================

CHIPMEMSIZE	= 524288
FASTMEMSIZE	= 0
NUMDRIVES	= 1
WPDRIVES	= %0000

BLACKSCREEN
;BOOTBLOCK
BOOTDOS
;BOOTEARLY
;CBDOSLOADSEG
;CBDOSREAD
;CACHE
;DEBUG ; enable only for a local diagnostic build
;DISKSONBOOT
DOSASSIGN
FONTHEIGHT	= 8
HDINIT
;HRTMON
;INITAGA
;INIT_AUDIO
;INIT_GADTOOLS
;INIT_LOWLEVEL
;INIT_MATHFFP
IOCACHE		= 1024
;JOYPADEMU
;MEMFREE	= $200
;NEEDFPU
;NO68020
POINTERTICKS	= 1
;PROMOTE_DISPLAY
;STACKSIZE	= 16384
;TRDCHANGEDISK

;============================================================================

slv_Version	= 17
slv_Flags	= WHDLF_NoError|WHDLF_Examine|WHDLF_ClearMem
slv_keyexit	= $59	; F10

;============================================================================

	INCLUDE	Sources:whdload/kick13.s

;============================================================================


slv_CurrentDir	IFD	DEBUG
		dc.b	"SOURCES:WHD_Slaves/FerrariFormulaOne/data",0
		ELSE
		dc.b	"data",0
		ENDIF

slv_name	dc.b	"Ferrari Formula One",0
slv_copy	dc.b	"1988 Electronic Arts",0
slv_info	dc.b	"installed by StingRay/[S]carab^Scoopex",10
		IFD	DEBUG
		dc.b	"DEBUG!!! "
		ENDC
		dc.b	"Version 2.0b (11.11.2026)",0
		CNOP	0,4

slv_config	dc.b	"C2:B:Enhanced framerate"
		dc.b	0
		CNOP	0,4

TAGLIST		dc.l	WHDLTAG_CUSTOM2_GET
FF1PublicEnabled	dc.l 0
	dc.l	WHDLTAG_ATTNFLAGS_GET
FF1AttnFlags	dc.l	0
	dc.l	TAG_DONE
DOSbase	dc.l	0

	IFD BOOTDOS

_bootdos
	lea	.saveregs(pc),a0
	movem.l	d1-d3/d5-d7/a1-a2/a4-a6,(a0)

	lea	_dosname(pc),a1
	move.l	$4.w,a6
	jsr	_LVOOldOpenLibrary(a6)
	move.l	d0,a6
	lea	DOSbase(pc),a0
	move.l	d0,(a0)

	lea	TAGLIST(pc),a0
	move.l	_resload(pc),a2
	jsr	resload_Control(a2)

	lea	.disk(pc),a0
	sub.l	a1,a1
	bsr	_dos_assign
	lea	.df0(pc),a0
	sub.l	a1,a1
	bsr	_dos_assign

	lea	.game(pc),a0
	jsr	resload_GetFileSize(a2)
	lea	PLGAME(pc),a5
	cmp.l	#199368,d0			; SPS 481
	beq.b	.ok
	lea FF1PublicEnabled(pc),a0
	clr.l (a0)
	lea	PLGAME_IREK(pc),a5		; version sent by Irek
	cmp.l	#199500,d0			; (later version with
	beq.b	.ok				; bugs fixed)

	pea	(TDREASON_WRONGVER).w
	bra.w	EXIT


; load game and patch game
.ok	lea	.game(pc),a0
	move.l	a0,d1
	bsr.w FF1PublicBoot
	jsr	_LVOLoadSeg(a6)
	lea FF1PublicRoot(pc),a0
	move.l d0,(a0)
	move.l	d0,d7
	
	move.l	a5,a0
	move.l	d7,a1
	jsr	resload_PatchSeg(a2)
	bsr.w FF1AudioDelayPatch
	bsr.w FF1PublicResident

	move.l	d7,d1
	moveq	#.arglen,d0
	lea	.args(pc),a0


; d0.l: argument length
; d1.l: segment
; a0.l: argument (command line)
; a6.l: dosbase
.call	lea	.callregs(pc),a1
	movem.l	d2-d7/a2-a6,(a1)
	move.l	(a7)+,11*4(a1)
	move.l	d0,d4
	lsl.l	#2,d1
	move.l	d1,a3
	move.l	a0,a4		; save command line
; create longword aligned copy of args
	lea	.callargs(pc),a1
	move.l	a1,d2
.copy	move.b	(a0)+,(a1)+
	subq.w	#1,d0
	bne.b	.copy

; set args
	jsr	_LVOInput(a6)
	lsl.l	#2,d0		; BPTR -> APTR
	move.l	d0,a0
	lsr.l	#2,d2		; APTR -> BPTR
	move.l	d2,fh_Buf(a0)
	clr.l	fh_Pos(a0)
	move.l	d4,fh_End(a0)
; call
	move.l	d4,d0
	move.l	a4,a0


	movem.l	.saveregs(pc),d1-d3/d5-d7/a1-a2/a4-a6

FF1PublicCallSite equ *
	jsr	4(a3)


; return
	movem.l	.callregs(pc),d2-d7/a2-a6
	move.l	.callrts(pc),a0
	jmp	(a0)







.game	dc.b	"racemenu",0
.df0	dc.b	"df0",0
.disk	dc.b	"ff1",0
.args	dc.b	"",10		; must be LF terminated
.arglen	= *-.args
	CNOP	0,4

.saveregs	ds.l	11
.saverts	dc.l	0
.dosbase	dc.l	0
.callregs	ds.l	11
.callrts	dc.l	0
.callargs	ds.b	208


EXIT	move.l	_resload(pc),a2
	jmp	resload_Abort(a2)


	CNOP 0,4


PLGAME_IREK
	PL_START
	PL_SA	$7dc,$862
	PL_W	$862,$7000+16		; moveq	#16,d0
	PL_SA	$868,$8a4

	PL_PS	$2e6,.patchhunk

	PL_S	$816,4			; skip delay
	PL_S	$8d0,4			; skip delay
	PL_P	$22a2,fixdelay		; fix CPU dependent delay
	PL_END


.patchhunk
	add.l	$1c(a3),d0
	move.l	d0,a1


; check if it is the "Race" hunk
; hunk starts at $64ae0
	cmp.w	#$2250,$6662(a1)	; $6b0ca
	bne.b	.no


; fix timing
	move.w	#$4eb9,$6a304-$64a68(a1)
	pea	fixtiming(pc)
	move.l	(a7)+,$6a304-$64a68+2(a1)

.no	rts


; d0.w: delay value
fixdelay
	movem.l	d0/a0,-(a7)
	lsl.w	#2,d0
	move.l	_resload(pc),a0
	jsr	resload_Delay(a0)
	movem.l	(a7)+,d0/a0
	rts

PLGAME	PL_START

; disable protection checks

	PL_SA	$770,$7f6
	PL_W	$7f6,$7000+16		; moveq	#16,d0
	PL_SA	$7fc,$838


	PL_PS	$2e6,.patchhunk

	PL_S	$7aa,4			; skip delay
	PL_S	$864,4			; skip delay
	PL_P	$2236,fixdelay		; fix CPU dependent delay
	PL_END


.patchhunk
	add.l	$1c(a3),d0
	move.l	d0,a1

 move.l d1,-(sp)
 move.l FF1PublicEnabled(pc),d1
 movem.l (sp)+,d1
 beq.w .legacy_layout
 cmpi.l #$22f30,(a3)
 bne.w .no
 movem.l d0-d7/a0-a6,-(sp)
 move.l a4,a0
 move.l $18(a3),d0
 lsl.l #2,d0
 suba.l d0,a0
 lea .patch(pc),a1
 lea fixtiming(pc),a2
 moveq #1,d0 ; elapsed mode replaces the native timing callback
 bsr.w FF1PatchPublicRace
 lea FF1PublicPatchError(pc),a0
 move.l d0,(a0)
 tst.l d0
 bne.w FF1WrongVersion
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w FF1Dispatch
 bra.w .no
.legacy_layout:
; check if it is the "Race" hunk
; hunk starts at $64a68
	cmp.w	#$2250,$6662(a1)	; $6b0ca
	bne.b	.no

; fix bug with setting 2nd screen ptr
	move.w	#$4eb9,$65518-$64a68(a1)
	pea	.patch(pc)
	move.l	(a7)+,$65518-$64a68+2(a1)

; fix wrong blit
	move.w	#$9240,$6b0ba-$64a68(a1)	; sub.l d0,d1 -> sub.w d0,d1


; fix timing
	move.w	#$4eb9,$6a304-$64a68(a1)
	pea	fixtiming(pc)
	move.l	(a7)+,$6a304-$64a68+2(a1)

	IFD	DEBUG
.RMB	move.w	#$f00,$dff180
	btst	#2,$dff016
	bne.b	.RMB
	ENDC


.no	rts


.patch	asl.l	#2,d0			; original code
	asl.l	#2,d0
	move.l	d0,a0

	ext.l	d1			; fix!

	move.w	d1,$dff180
	rts



fixtiming
;	move.w	#$f00,$dff180

	asl.w	#1,d0			; original code
	ext.l	d0
	move.l	d0,a4

.timing	movem.l	d0-a6,-(a7)
	move.l	$4.w,a6
	move.l	$9c(a6),a6
	jsr	-270(a6)
	jsr	-270(a6)
	movem.l	(a7)+,d0-a6
	rts

	ENDC ; close published BOOTDOS conditional for vasm

FF1PublicResident:
 movem.l d0-d7/a0-a6,-(sp)
 move.l FF1PublicEnabled(pc),d0
 beq.b .done
 move.l d7,d0
 lsl.l #2,d0
 move.l d0,a0
 move.l 4+16(a0),d0
 lsl.l #2,d0
 move.l d0,a0
 bsr.w FF1PreparePublicResident
 tst.l d0
 beq.b .flush
 pea (TDREASON_WRONGVER).w
 bra.w EXIT
.flush:
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
; The game's audio interrupt (SPS 0481: root hunk 41, +$70) stops a channel whose
; sample queue has run dry: volume 0, period 124, a 400-iteration CPU loop, then DMA
; off. Paula keeps playing a channel whose DMA goes off and raises its interrupt
; after every sample word (2 x 124 colour clocks, 70 us), unless the previous one is
; still pending, which stops the channel. The handler clears it on entry, so the
; channel stops only if the handler outlasts two words. On a 68000 the loop lasts
; about 1 ms and it does. A cached 68040/060 leaves the loop within one word: the
; interrupt then comes every 70 us and runs this path each time, which stalls the
; game for seconds (a1200-060 in the emulator, at the Spa start). On a 68020 or
; faster the loop becomes a 5-line beam wait (at least 256 us); the 68000 and 68010
; keep it. The path is found by its 22 bytes: at hunk 41, or for another layout
; anywhere in the root segments. D7 = root segment list (BPTR). All registers preserved.
FF1AudioDelayPatch:
 movem.l d0-d2/a0-a1,-(sp)
 move.l FF1AttnFlags(pc),d0
 btst #AFB_68020,d0
 beq.b .done
 move.l d7,d0
 moveq #41-1,d1
.walk:
 lsl.l #2,d0
 beq.b .scanall
 move.l d0,a0
 move.l (a0),d0
 dbf d1,.walk
 lsl.l #2,d0
 beq.b .scanall
 move.l d0,a0
 lea 4+$70(a0),a0
 bsr.b .match
 beq.b .found
.scanall:
 move.w #$317c,d1
 move.l d7,d0
.seg:
 lsl.l #2,d0
 beq.b .done
 move.l d0,a1
 move.l -4(a1),d2		; segment: allocation size, next BPTR, code
 sub.l #8+22,d2
 bmi.b .next
 lsr.l #1,d2
 lea 4(a1),a0
.scan:
 cmp.w (a0),d1
 bne.b .skip
 bsr.b .match
 beq.b .found
.skip:
 addq.l #2,a0
 subq.l #1,d2
 bpl.b .scan
.next:
 move.l (a1),d0
 bra.b .seg
.found:
 move.w #$4eb9,$c(a0)		; JSR FF1AudioDelay, NOP, NOP over the loop
 pea FF1AudioDelay(pc)
 move.l (sp)+,$e(a0)
 move.l #$4e714e71,$12(a0)
 move.l _resload(pc),a0
 jsr resload_FlushCache(a0)
.done:
 movem.l (sp)+,d0-d2/a0-a1
 rts
; Z set if A0 is at MOVE.W #0,8(A0); MOVE.W #$7C,6(A0); MOVE.W #$190,D0;
; SUBI.W #1,D0; BNE.B *-4.
.match:
 cmpi.l #$317c0000,(a0)
 bne.b .no
 cmpi.l #$0008317c,4(a0)
 bne.b .no
 cmpi.l #$007c0006,8(a0)
 bne.b .no
 cmpi.l #$303c0190,12(a0)
 bne.b .no
 cmpi.l #$04400001,16(a0)
 bne.b .no
 cmpi.w #$66fa,20(a0)
.no:
 rts

; At least 4 full beam lines (the line byte of VHPOSR changing 5 times). D0 = 0, as
; the replaced loop left it.
FF1AudioDelay:
 move.l d1,-(sp)
 moveq #5-1,d1
.line:
 move.b $dff006,d0
.same:
 cmp.b $dff006,d0
 beq.b .same
 dbf d1,.line
 move.l (sp)+,d1
 moveq #0,d0
 rts
FF1PublicPatchError: dc.l 0
FF1PublicBoot:
 movem.l d0-d7/a0-a6,-(sp)
 move.l FF1PublicEnabled(pc),d0
 beq.w .done
 move.l FF1ProfileMonitor(pc),d0
 cmpi.l #$00021000,d0 ; PAL_MONITOR_ID (graphics/modeid.i)
 bne.w FF1RequirePAL
 lea FF1PublicPool(pc),a0
 move.l _expmem(pc),a1
 adda.l #$40000,a1
 move.l #FF1_EXPMEM_SIZE-$40000,d0
 move.l a0,-(sp)
 move.l a1,d2
 move.l #FF1_EXPMEM_SIZE-$40000,d3
 moveq #1,d0
 moveq #2,d1
 bsr.w FF1SelectProfile
 moveq #1,d1
 cmpi.l #2,d0
 bne.b .attrs
 moveq #5,d1
.attrs:
 move.l (sp)+,a0
 move.l #FF1_EXPMEM_SIZE-$40000,d0
 bsr.w FF1PublicPoolOpen
 tst.l d0
 bne.w FF1WrongVersion
 lea FF1PublicCallSite(pc),a0
 move.w #$6100,(a0)
 move.w #FF1PublicCall-FF1PublicCallSite-2,2(a0)
 move.l _resload(pc),a2
 jsr resload_FlushCache(a2)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
FF1PublicPool: ds.l 2
FF1PublicRoot: dc.l 0
FF1PublicMarker: dc.b 'FF1B7PUBLICROOT',0,0
 even
 include "FerrariFormulaOne_PublicMemory.s"
 include "FerrariFormulaOne_PublicLoader.s"
 include "FerrariFormulaOne_PublicStack.s"
 include "FerrariFormulaOne_Cache.s"

 include "ProductionHost.s"
