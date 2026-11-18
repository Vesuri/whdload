;*---------------------------------------------------------------------------
;  :Program.	wildwestworld.asm
;  :Contents.	Slave for "Wild West World" from Software 2000
;  :Author.	Wepl
;  :Original	v1 
;  :Version.	$Id: wildwestworld.asm 1.2 2002/02/08 01:18:39 wepl Exp wepl $
;  :History.	07.08.00 started
;		03.08.01 some steps forward ;)
;		30.01.02 final beta
;  :Requires.	-
;  :Copyright.	Public Domain
;  :Language.	68000 Assembler
;  :Translator.	Devpac 3.14, Barfly 2.9
;  :To Do.
;---------------------------------------------------------------------------*

	INCDIR	Include:
	INCDIR	osemu:
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	INCLUDE	lvo/dos.i

	IFD BARFLY
	OUTPUT	"Gunship2000AGA.slave"
	BOPT	O+				;enable optimizing
	BOPT	OG+				;enable optimizing
	BOPT	ODd-				;disable mul optimizing
	BOPT	ODe-				;disable mul optimizing
	BOPT	w4-				;disable 64k warnings
	BOPT	wo-			;disable optimizer warnings
	SUPER
	ENDC

;============================================================================

CHIPMEMSIZE	= $100000
FASTMEMSIZE	= $100000
NUMDRIVES	= 1
WPDRIVES	= %1111
;DEBUG
;DISKSONBOOT
DOSASSIGN
HDINIT
INITAGA
IOCACHE		= 10000
;MEMFREE	= $200
;NEEDFPU
;SETPATCH
CBDOSLOADSEG
BOOTDOS
STACKSIZE = 13000
; The instruction cache for all memory. JOTD's CACHE marks BaseMem non-cacheable, and
; without WHDLoad's MMU (its default on a 68030) that switches both caches off.
CACHECHIP

;============================================================================


slv_Version	= 17
slv_Flags	= WHDLF_NoError|WHDLF_Examine|WHDLF_ClearMem
slv_keyexit	= $5D	; num '*'

;============================================================================

	include	whdload/kick31.s

;============================================================================

	IFD BARFLY
	DOSCMD	"WDate  >T:date"
	ENDC

_dsk1
	dc.b	"gs_dsk1",0
_dsk2
	dc.b	"gs_dsk2",0
_dsk3
	dc.b	"gs_dsk3",0
_dsk4
	dc.b	"gs_dsk4",0
_env
	dc.b	"ENV",0


DECL_VERSION:MACRO
	incbin	"slave_version"
	IFD BARFLY
		dc.b	" "
		INCBIN	"T:date"
	ENDC
	ENDM

slv_name		dc.b	"Gunship 2000 AGA",0
slv_copy		dc.b	"1993 Microprose",0
slv_info		dc.b	"adapted by JOTD",10
		dc.b	"enhanced by Vesuri",10,10
		dc.b	"Version "
		DECL_VERSION
		dc.b	0
slv_config	dc.b	"C2:B:Enhanced framerate;"
		dc.b	0
slv_CurrentDir:
	dc.b	"data",0
	EVEN

_program:
	dc.b	"Gunship 2000",0
_args		dc.b	10
_args_end
	dc.b	0
	cnop	0,4
_rampath:
	dc.b	"RAM:",0

	dc.b	"$","VER: Gunship2000AGA.slave "
	DECL_VERSION
	dc.b	$A,$D,0

	EVEN


;============================================================================

	;initialize kickstart and environment

; < D0: BSTR filename
; < D1: seglist
_cb_dosLoadSeg
	clr.l	0

	; now D1 is start address

	lsl.l	#2,d0
	move.l	d0,a0

	bsr	.strip_colon
	cmp.b	#'g',(A0)
	bne.b	.nomain
	cmp.b	#'s',1(A0)
	bne.b	.nomain
	cmp.b	#'2',2(A0)
	beq.b	.gs2_run
	tst.b	2(a0)
	bne.b	.nomain

	; gs file

	bsr	.patch_gs_segments
	bra.b	.noboot

	; gs2.run file
.gs2_run
	cmp.b	#'.',3(A0)
	bne.b	.nomain
	bsr	.patch_gs2_run_segments
	bra.b	.noboot

.nomain:
	cmp.b	#'G',(A0)
	bne.b	.noboot
	cmp.b	#'u',1(A0)
	bne.b	.noboot
	move.l	d1,d7
	bsr	_patch_exe
.noboot
	rts

.strip_colon
	addq.l	#1,a0
	movem.l	a0,-(a7)
.loop
	move.b	(a0)+,d0
	beq.b	.fail
	cmp.b	#':',d0
	bne.b	.loop
	addq.l	#4,a7
	rts	
.fail
	movem.l	(a7)+,a0
	rts

; file "gs"

.patch_gs_segments:
	move.l	d1,a1
	add.l	a1,a1
	add.l	a1,a1
	addq.l	#4,a1

	patch	$D0,crack

	IFD VERIFY
	move.l	d1,-(a7)
	ENDC
	lea	pl_gs(pc),a0
	move.l	_resload(pc),a2
	jsr	resload_Patch(a2)

	IFD VERIFY
	; The same mission on every machine and slave. random() (hunk 97) seeds from time() on
	; its first call: a constant instead. The office animations then call it a
	; timing-dependent number of times, so the mission setup in hunk 22 (time of day, ...)
	; also reseeds.
	move.l	(a7),d1
	moveq	#0,d0
	bsr	.gs_hunk
	move.l	$35c6(a1),d0		; rand's move.w seed,d0: the seed's address
	lea	verify_seed(pc),a0
	move.l	d0,(a0)
	moveq	#97,d0
	bsr	.gs_hunk
	lea	pl_gs_97(pc),a0
	jsr	resload_Patch(a2)
	move.l	(a7)+,d1		; resload_Patch may change D1
	moveq	#22,d0
	bsr	.gs_hunk
	lea	pl_gs_22(pc),a0
	jsr	resload_Patch(a2)
	ENDC

	rts

; < D0: hunk number, D1: seglist   > A1: the hunk's start
.gs_hunk
	move.l	d1,a1
	bra.b	.gs_hunk_next
.gs_hunk_loop
	move.l	(a1),a1
.gs_hunk_next
	add.l	a1,a1
	add.l	a1,a1
	dbf	d0,.gs_hunk_loop
	addq.l	#4,a1
	rts

; file "gs2.run"

.patch_gs2_run_segments:
	move.l	d1,a1
	add.l	a1,a1
	add.l	a1,a1
	addq.l	#4,a1
	move.l	d1,-(a7)
	lea	pl_gs2_run(pc),a0
	move.l	_resload(pc),a2
	jsr	resload_Patch(a2)

	; CUSTOM2=1: the frame rate is no longer capped (fps_* below)
	lea	_ctltags(pc),a0
	jsr	resload_Control(a2)
	move.l	(a7)+,d1		; resload_* may change D1
	move.l	_custom2(pc),d0
	beq.b	.nofps
	move.l	d1,-(a7)
	moveq	#2,d0
	bsr	.gs_hunk
	lea	gs2_bss(pc),a0
	move.l	a1,(a0)
	move.l	(a7)+,d1
	moveq	#0,d0
	bsr	.gs_hunk
	lea	gs2_code(pc),a0
	move.l	a1,(a0)
	lea	pl_gs2_fps(pc),a0
	move.l	a1,-(a7)
	jsr	resload_Patch(a2)
	move.l	(a7)+,a1
	bsr	fps_dither_sites
	jsr	resload_FlushCache(a2)
.nofps
	rts

_ctltags	dc.l	WHDLTAG_CUSTOM2_GET
_custom2	dc.l	0
	IFD VERIFY
		dc.l	WHDLTAG_CUSTOM3_GET
_custom3	dc.l	0	; VERIFY: frames of at least this many fields (CUSTOM2=1)
	ENDC
		dc.l	TAG_DONE

pl_gs
	PL_START
	PL_L	$4970,$4EB800D0	; crack
	PL_END

	IFD VERIFY
pl_gs_97
	PL_START
	PL_L	$aa,$70014E71		; move.l -4(a5),d0 (the time) -> moveq #1,d0
	PL_END

pl_gs_22
	PL_START
	PL_PS	$2a40,reseed_mission	; moveq #0,d0; move.l d0,d5; move.w d5,-18(a5)
	PL_NOP	$2a46,2
	PL_END
	ENDC

pl_gs2_run
	PL_START
	PL_L	$12780,$4E714E71	; remove WaitTOF before LoadView
	PL_PS	$12834,set_copperlist
	PL_PS	$13d52,fast_stack	; keep the stack in fast memory
	PL_S	$13d58,$13d62-$13d58
	IFD VERIFY
	PL_PS	$183e8,seed_flight	; move.w VHPOSR,bss+$b8fe: the flight's random seed
	ENDC
;;	PL_P	$13E6A,quit
	PL_END

; CUSTOM2=1. The frame loop (code $28-$304) waited for 6 ticks of the 64 Hz CIA-B timer a
; frame (at most 10.67 fps) and stepped the simulation by the ticks since the last frame.
; Now a frame takes at least one field, and the step is the fields since the last frame
; (frames are presented on the VBL anyway, COP1LC), with the remainders carried:
pl_gs2_fps
	PL_START
	PL_PS	$28,fps_dt		; dt from the fields, not the ticks
	PL_S	$2e,$4a-$2e
	PL_PS	$78,fps_clock		; the mission clock's add, remainder carried
	PL_S	$7e,$86-$7e
	PL_PS	$2a8,fps_phase		; the per-frame phases every 6 ticks of game time
	PL_S	$2ae,$2bc-$2ae
	PL_PS	$2c6,fps_wait		; the cap: one field instead of 6 ticks
	PL_S	$2cc,$2d2-$2cc
	PL_PS	$2fe,fps_blink		; likewise the blink
	PL_PS	$608,fps_vbl		; count the fields (not while paused)
	PL_PS	$18430,fps_start	; the flight's first frame
	PL_NOP	$18436,2
	PL_PS	$7716,fps_speed		; the speed's approach once per 6 ticks
	PL_NOP	$771c,2
	PL_PS	$7950,fps_climb		; the climb rate's approach once per 6 ticks
	PL_NOP	$7956,2
	PL_PS	$1212,fps_collective	; the collective keys once per 6 ticks
	PL_PS	$1268,fps_collective
	PL_END

; The flight moved its stack onto the first 2000 bytes of its chip work area (heap pointer
; data+$2c3e). Stay on the process stack (ExpMem) and still take the 2000 bytes, so the
; heap is laid out as before. A5 = data+$2dfc, where the process stack pointer was saved.
fast_stack
	add.l	#2000,-($2dfc-$2c3e)(a5)
	rts

	IFD VERIFY
verify_seed
	dc.l	0

reseed_mission
	move.l	a0,-(a7)
	move.l	verify_seed(pc),a0
	move.w	#1,(a0)
	move.l	(a7)+,a0
	moveq	#0,d0
	move.l	d0,d5
	move.w	d5,-18(a5)
	rts

; A constant flight seed; the seed's address is the instruction's operand after the jsr.
seed_flight
	move.l	a0,-(a7)
	move.l	4(a7),a0
	move.l	(a0),a0
	move.w	#1,(a0)
	move.l	(a7)+,a0
	addq.l	#4,(a7)
	rts
	ENDC

; Enhanced framerate (CUSTOM2=1). dt (bss+$c67e) is 32768 per 15 ticks of 64 Hz; per
; field that is 2097152/750 on PAL (50 Hz), 2097152/900 on NTSC (60 Hz).
gs2_bss		dc.l	0
gs2_code	dc.l	0
fps_k		dc.w	0	; 6-tick periods this simulation step completes
fps_fields	dc.w	0	; fields since the last frame, counted while not paused
fps_shift	dc.w	20	; dt = (fields << shift + fps_rem) / fps_den
fps_den		dc.w	375
fps_max		dc.w	11	; more fields: dt 32767, the game's own clamp (15 ticks)
fps_rem		dc.w	0
fps_crem	dc.l	0	; the clock's remainder, 32nds
fps_pacc	dc.l	0	; game time toward the next phase step, dt * 5 (65536 = 6 ticks)
fps_bacc	dc.l	0	; the same for the blink

; code $18430, the flight's setup: move.w #15,bss+$c680 (the ticks)
fps_start
	movem.l	d0-d3/a0,-(a7)
	move.l	gs2_bss(pc),a0
	move.w	#15,$c680(a0)
	lea	fps_fields(pc),a0
	move.w	#99,(a0)		; the first frame: dt 32767, as the game's 15 ticks
	clr.w	fps_rem-fps_fields(a0)
	clr.l	fps_crem-fps_fields(a0)
	clr.l	fps_pacc-fps_fields(a0)
	clr.l	fps_bacc-fps_fields(a0)
	; PAL or NTSC from the highest line of a field (WHDLoad's PAL/NTSC options included)
	bsr	.line
.wrap	move.w	d0,d1
	bsr	.line
	cmp.w	d1,d0
	bhs.b	.wrap
	moveq	#0,d2
.field	cmp.w	d2,d0
	bls.b	.next
	move.w	d0,d2
.next	move.w	d0,d1
	bsr	.line
	cmp.w	d1,d0
	bhs.b	.field
	move.l	#(20<<16)|375,d0	; PAL
	moveq	#11,d1
	cmp.w	#288,d2
	bhs.b	.pal
	move.l	#(19<<16)|225,d0	; NTSC: 2097152/900 = 524288/225
	moveq	#14,d1
.pal	move.l	d0,fps_shift-fps_fields(a0)
	move.w	d1,fps_max-fps_fields(a0)
	movem.l	(a7)+,d0-d3/a0
	rts
; > D0.w: the beam's line, read until two reads agree
.line	move.l	$dff004,d0
	lsr.l	#8,d0
	and.w	#$1ff,d0
	move.l	$dff004,d3
	lsr.l	#8,d3
	and.w	#$1ff,d3
	cmp.w	d0,d3
	bne.b	.line
	rts

; code $608, the VBL client: addq.w #1,bss+$b8fc
fps_vbl
	move.l	a0,-(a7)
	move.l	gs2_bss(pc),a0
	addq.w	#1,$b8fc(a0)
	tst.b	$c738(a0)		; paused: the CIA-B server stops the ticks too
	bne.b	.paused
	lea	fps_fields(pc),a0
	addq.w	#1,(a0)
.paused	move.l	(a7)+,a0
	rts

; code $28: > D0.w = bss+$c67e = dt for the fields since the last frame
fps_dt
	movem.l	d1/a0-a1,-(a7)
	move.l	gs2_bss(pc),a0
	clr.w	$c680(a0)
	lea	fps_fields(pc),a1
	moveq	#0,d0
	move.w	(a1),d0
	sub.w	d0,(a1)			; one instruction: no field lost to the VBL
	cmp.w	fps_max-fps_fields(a1),d0
	bls.b	.step
	clr.w	fps_rem-fps_fields(a1)
	move.w	#32767,d0
	bra.b	.set
.step	move.w	fps_shift-fps_fields(a1),d1
	lsl.l	d1,d0
	moveq	#0,d1
	move.w	fps_rem-fps_fields(a1),d1
	add.l	d1,d0
	divu.w	fps_den-fps_fields(a1),d0
	swap	d0
	move.w	d0,fps_rem-fps_fields(a1)
	swap	d0
.set	move.w	d0,$c67e(a0)
	movem.l	(a7)+,d1/a0-a1
	rts

; code $78: > D0.w = dt * 15360 / 32768 (= dt * 15 / 32), the remainder carried
fps_clock
	movem.l	d1/a0-a1,-(a7)
	move.l	gs2_bss(pc),a0
	lea	fps_pacc(pc),a1
	bsr	fps_steps
	lea	fps_k(pc),a1
	move.w	d0,(a1)			; this step's 6-tick periods
	moveq	#0,d0
	move.w	$c67e(a0),d0
	mulu.w	#15,d0
	lea	fps_crem(pc),a0
	add.l	(a0),d0
	moveq	#31,d1
	and.l	d0,d1
	move.l	d1,(a0)
	lsr.l	#5,d0
	movem.l	(a7)+,d1/a0-a1
	rts

; code $2a8, once per simulation step: not.b bss+$c68b; bss+$c68c = (bss+$c68c + 1) & 3,
; now once per 6 ticks of game time
fps_phase
	movem.l	d0/a0,-(a7)
	move.l	gs2_bss(pc),a0
	move.w	fps_k(pc),d0
	bra.b	.test
.step	not.b	$c68b(a0)
	addq.b	#1,$c68c(a0)
	and.b	#3,$c68c(a0)
.test	dbf	d0,.step
	movem.l	(a7)+,d0/a0
	rts

; What the flight model does per step without dt, at the cap once per 6 ticks, now once per
; 6 ticks of game time (fps_k times a step), so it keeps its rate.

; code $7716: bsr $7c04 (the speed approaches its target by 1/8 or 1/16 of the gap, or 1);
; bsr $7dda (the heading)
fps_speed
	movem.l	d0/a0,-(a7)
	move.w	fps_k(pc),d0
	bra.b	.test
.step	movem.l	d0-a6,-(a7)
	move.l	gs2_code(pc),a0
	jsr	$7c04(a0)
	movem.l	(a7)+,d0-a6
.test	dbf	d0,.step
	movem.l	(a7)+,d0/a0
	move.l	gs2_code(pc),-(a7)	; then $7dda, returning to $771c
	add.l	#$7dda,(a7)
	rts

; code $7950: asr.w #2,d1; add.w d1,bss+$2cc (the climb rate moves a quarter of the way to
; bss+$2ca, or the rest when within 16); D1 = bss+$2ca - bss+$2cc, more than 16 apart
fps_climb
	movem.l	d0/d2/a0,-(a7)
	move.l	gs2_bss(pc),a0
	move.w	fps_k(pc),d0
	bra.b	.test
.step	move.w	$2ca(a0),d1
	sub.w	$2cc(a0),d1
	move.w	d1,d2
	bpl.b	.pos
	neg.w	d2
.pos	cmp.w	#16,d2
	bgt.b	.quarter
	move.w	$2ca(a0),$2cc(a0)
	bra.b	.done
.quarter
	asr.w	#2,d1
	add.w	d1,$2cc(a0)
.test	dbf	d0,.step
.done	movem.l	(a7)+,d0/d2/a0
	rts

; codes $1212 and $1268, the keys = and - (collective up and down): clr.w bss+6, then a step
; of the collective each time they are called (each simulation step the key is held)
fps_collective
	tst.w	fps_k(pc)
	beq.b	.skip
	move.l	a0,-(a7)
	move.l	gs2_bss(pc),a0
	clr.w	6(a0)
	move.l	(a7)+,a0
	rts
.skip	addq.l	#4,a7			; not this step: return from the key's routine
	rts

; code $2fe, once per frame: not.b bss+$c68a (a blink), now once per 6 ticks
fps_blink
	movem.l	d0/a0-a1,-(a7)
	move.l	gs2_bss(pc),a0
	lea	fps_bacc(pc),a1
	bsr.b	fps_steps
	btst	#0,d0
	beq.b	.even
	not.b	$c68a(a0)
.even	movem.l	(a7)+,d0/a0-a1
	rts

; < A0: bss, A1: an accumulator   > D0.w: how many 6-tick periods dt completes
fps_steps
	move.l	d1,-(a7)
	moveq	#0,d0
	move.w	$c67e(a0),d0
	mulu.w	#5,d0
	add.l	(a1),d0
	moveq	#0,d1
	move.w	d0,d1
	move.l	d1,(a1)
	clr.w	d0
	swap	d0
	move.l	(a7)+,d1
	rts

; The simulation's x * dt products, muls.w bss+$c67e,Dn; add.l Dn,Dn; swap Dn (84 of them),
; truncate: a frame loses up to one unit of each, so at small dt slow processes (the bank
; levelling out, ...) lose a larger share. Each becomes jsr fps_dtm<n>; nop; swap Dn, which adds
; a uniform fraction before the swap: the result is right on average, and 0 stays 0.
; < A1: gs2.run's code
fps_dither_sites
	movem.l	d0-d4/a0-a2,-(a7)
	move.l	gs2_bss(pc),d1
	add.l	#$c67e,d1
	lea	fps_dtp(pc),a0
	move.l	d1,(a0)
	lea	$19014-10(a1),a2	; the code hunk's size
	lea	fps_dtm0(pc),a0
	moveq	#0,d4
.scan	move.w	(a1),d0
	move.w	d0,d2
	and.w	#$f1ff,d2
	cmp.w	#$c1f9,d2		; muls.w abs.l,Dn
	bne.b	.next
	cmp.l	2(a1),d1
	bne.b	.next
	move.w	d0,d2
	and.w	#$0e00,d2		; Dn << 9
	move.w	d2,d3
	or.w	#$d080,d3		; add.l Dn,Dn
	lsr.w	#8,d2
	lsr.w	#1,d2
	or.w	d2,d3
	cmp.w	6(a1),d3
	bne.b	.next
	move.w	d2,d3
	or.w	#$4840,d3		; swap Dn
	cmp.w	8(a1),d3
	bne.b	.next
	mulu.w	#fps_dtm1-fps_dtm0,d2
	add.l	a0,d2
	move.w	#$4eb9,(a1)		; jsr fps_dtm<n>
	move.l	d2,2(a1)
	move.w	#$4e71,6(a1)		; nop
	addq.w	#1,d4
	lea	10(a1),a1
	bra.b	.more
.next	addq.l	#2,a1
.more	cmp.l	a2,a1
	bls.b	.scan
	lea	fps_sites(pc),a0
	move.w	d4,(a0)
	movem.l	(a7)+,d0-d4/a0-a2
	rts

fps_sites	dc.w	0	; how many were patched (84)
fps_dtp		dc.l	0	; bss+$c67e
	cnop	0,4
fps_dither	dc.l	0	; the high word stays 0

DTM	MACRO
fps_dtm\1
	move.l	a0,-(a7)
	move.l	fps_dtp(pc),a0
	muls.w	(a0),d\1
	add.l	d\1,d\1
	lea	fps_dither(pc),a0
	add.w	#40503,2(a0)		; 65536 / the golden ratio: evenly spread
	add.l	(a0),d\1
	move.l	(a7)+,a0
	rts
	ENDM

	DTM	0
	DTM	1
	DTM	2
	DTM	3
	DTM	4
	DTM	5
	DTM	6
	DTM	7

; code $2c6: wait for a field since the last frame (then COP1LC shows this one)
fps_wait
	move.l	a0,-(a7)
	lea	fps_fields(pc),a0
	IFD VERIFY
	move.l	d0,-(a7)
	move.l	_custom3(pc),d0
	bne.b	.min
	moveq	#1,d0
.min	cmp.w	(a0),d0
	bhi.b	.min
	move.l	(a7)+,d0
	ELSE
.wait	tst.w	(a0)
	beq.b	.wait
	ENDC
	move.l	(a7)+,a0
	rts

quit
	pea	TDREASON_OK
	move.l	_resload(pc),-(a7)
	addq.l	#resload_Abort,(a7)
	rts

set_copperlist
	move.l	#$FFFFFFFE,0.W	; fixes hazard on copjmp2 to 0

	; code below actually not needed, but could be useful to fix
	; some copperlist entries

	movem.l	a0,-(a7)
	move.l	4(a7),a0	; return address
	move.l	2(a0),a0	; copperlist variable
	lea	$dff000,a5
	move.l	(a0),$80(a5)
	tst.w	$88(a5)
	movem.l	(a7)+,a0
	addq.l	#4,a7
	rts

crack
	; d7 contains the code to enter
	; a1 contains the string of the code entered by the user

	cmp.b	#':',(a1)
	beq.b	.notyet

	; wait till the user entered 5 digits (or else it does not work)

	movem.l	a0/d1/d2,-(a7)
	MOVE.L	D7,D1			;00: 2207
	LSR	#1,D1			;02: E249
	MOVEQ	#0,D2			;04: 7400
	MOVE	D1,D2			;06: 3401
	MOVEQ	#0,D1			;08: 7200
	MOVE	D7,D1			;0A: 3207
	ADD.L	D2,D1			; code

	MOVE.L	D1,-4(a5)		; replace code entered by the user

	move.l	a1,a0
	bsr	codetostring

	movem.l	(a7)+,a0/d1/d2

.notyet
	MOVE.L	-4(A5),D0	; code entered by the user
	RTS

codetostring:
	DIVU	#$2710,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	EXT.L	D1
	DIVU	#$03E8,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	EXT.L	D1
	DIVU	#$0064,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	EXT.L	D1
	DIVU	#$000A,D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)+
	SWAP	D1
	ADDI.B	#$30,D1
	MOVE.B	D1,(A0)
	RTS				;124: 4E75

_bootdos	move.l	(_resload),a2		;A2 = resload

	;open doslib
		lea	(_dosname,pc),a1
		move.l	(4),a6
		jsr	(_LVOOldOpenLibrary,a6)
		move.l	d0,a6			;A6 = dosbase

		lea	_env(pc),a0
		lea	_rampath(pc),a1
		bsr	_dos_assign
	;load exe
		lea	_program(pc),a0
		move.l	a0,d1
		jsr	(_LVOLoadSeg,a6)
		move.l	d0,d7			;D7 = segment
		beq	.end
	;call
		move.l	d7,a1
		add.l	a1,a1
		add.l	a1,a1

		move.l	(4,a7),d0		;stacksize
		sub.l	#5*4,d0			;required for MANX stack check

		movem.l	d0/d7/a2/a6,-(a7)

		moveq	#_args_end-_args,d0
		lea	(_args,pc),a0
		addq.l	#4,a1
		jsr	(a1)
		movem.l	(a7)+,d1/d7/a2/a6

	;remove exe
		move.l	d7,d1
		jsr	(_LVOUnLoadSeg,a6)

		pea	TDREASON_OK
		jmp	(resload_Abort,a2)

.end		moveq	#0,d0
		rts


_patch_exe:
	move.l	_resload(pc),a2
	move.l	d7,A1
	add.l	A1,A1
	add.l	A1,A1
	addq.l	#4,A1
	cmp.w	#$2C79,$66C(A1)
	beq.b	.ecs
	cmp.w	#$2C79,$512(A1)
	beq.b	.aga

	; wrong version

	pea	TDREASON_WRONGVER
	move.l	_resload(pc),-(a7)
	addq.l	#resload_Abort,(a7)
	rts

.ecs
	lea	_pl_gs2000_ecs(pc),a0
	bra.b	.patch
.aga
	lea	_pl_gs2000_aga(pc),a0
;	bra.b	.patch		; vasm: a bra.b to the next instruction is illegal; Barfly dropped it

.patch
	jsr	resload_Patch(a2)
	rts

_pl_gs2000_ecs:
	PL_START
	PL_P	$66C,move1d0rts
	PL_P	$78E,move1d0rts
	PL_END
_pl_gs2000_aga:
	PL_START
	PL_S	$122,$3E-$22		; skip test for "Install Gunship 2000"
	PL_S	$16C,$F4-$6C
;	PL_P	$512,assign_it
;	PL_P	$512,move1d0rts
;	PL_P	$634,move1d0rts
	PL_END

assign_it:
	move.l	a5,a0
	sub.l	a1,a1
move1d0rts
	moveq.l	#1,D0
	rts

;============================================================================

	END
