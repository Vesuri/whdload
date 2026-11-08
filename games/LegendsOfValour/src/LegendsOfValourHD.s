;*---------------------------------------------------------------------------
;  :Program.	LegendsOfValourHD.s
;  :Contents.	Slave for "Legends of Valour" (US Gold 1992), reconstructed
;  :Author.	CFou! (v1.0, 06.02.2005); reconstructed from the binary by Vesuri
;  :History.	05.10.26 rebuilt on WHDLoad 20.0's kick13.asm example (09.11.25) and
;			 kick13.s (07.11.25), game part from the v1.0 disassembly
;  :Requires.	WHDLoad 17+, whdload/kick13.s, kick34005.A500 + .RTB
;  :Language.	68000 Assembler
;  :Translator.	vasm (Devpac mode)
;---------------------------------------------------------------------------*
;
; No source of CFou!'s slave is public.  This file follows WHDLoad 20.0's kick13.asm slave
; example and rebuilds the game-specific part of the installed LegendsOfValour.Slave v1.0 from
; its disassembly (slave+$fa4.., docs/profiling.md §2).  It is not byte-identical: kick13.s is
; the 2025 one, v1.0 used 2005's.  Equivalence is checked by behaviour.
;
; Differences from v1.0, all deliberate:
; - kick13.s options as in the 2026 example (IOCACHE, CACHECHIP, SETPATCH, SEGTRACKER, ...).
;   Without IOCACHE every small Read() of the game is a resload call and, unless the file was
;   PRELOADed, a slow OS switch.
; - v1.0 opened AMIGA2, read 300 bytes and CRC16'd them, then ignored the result and left the
;   file open.  Dropped: _patchgame checks the bytes it patches.
; - The program is called with the example's .call (arguments through Input()), not jsr.
;
; AMIGA2 is a PowerPacker stub executable: hunk 0 decrunches hunk 1 and then loads the
; decrunched 17-hunk program itself.  The slave lets the stub run, takes over at its final
; "movem.l (a7)+,d0-a6 / rts" and patches the loaded program before entering it.
;
;---------------------------------------------------------------------------*

; VERIFY keeps independent performance switches for reproducible A/B captures.
; DEVELOPER also exposes them without including verification instruments.
        IFD VERIFY
        IFND DEVELOPER
DEVELOPER = 1
        ENDC
        ENDC

; Fixed-rate simulation. Historical build-flag names are retained
; for the recorded verification commands. Runtime CUSTOM2 bit 6 gates all
; installation, task creation and allocation; normal builds include both parts.
        IFND SIM_KEYBOARD_EXPERIMENT
SIM_KEYBOARD_EXPERIMENT = 1
        ENDC
        IFND SIM_COMBAT_EXPERIMENT
SIM_COMBAT_EXPERIMENT = 1
        ENDC

; The language of the game offsets (src/offsets.s): 0 English (0837), 1 German (0525),
; 2 French (1768). game.sh assembles all three with LOV_PASS1 and appends their differences
; to the English build as the fixup table that _lov_version applies (tools/fixups.py).
        IFND LOV_LANG
LOV_LANG = 0
        ENDC
LOV_EN = -(LOV_LANG=0)
LOV_DE = -(LOV_LANG=1)
LOV_FR = -(LOV_LANG=2)

	IFND __VASM
	INCDIR	Includes:
	ENDC
	INCLUDE	whdload.i
	INCLUDE	whdmacros.i
	INCLUDE	lvo/dos_lib.i
	INCLUDE	lvo/exec_lib.i
	INCLUDE	exec/memory.i
	INCLUDE	offsets.s

;============================================================================

CHIPMEMSIZE	= $80000	;size of chip memory (as v1.0)
FASTMEMSIZE	= $a4000	;original 512K + 144K reserve for optional ray table
NUMDRIVES	= 1		;amount of floppy drives to be configured
WPDRIVES	= %0000		;write protection of floppy drives

;BLACKSCREEN			;set all initial colors to black
;BOOTBLOCK			;enable _bootblock routine
BOOTDOS				;enable _bootdos routine
;BOOTEARLY			;enable _bootearly routine
;CBDOSLOADSEG			;enable _cb_dosLoadSeg routine
;CBDOSREAD			;enable _cb_dosRead routine
;CBKEYBOARD			;enable _cb_keyboard routine
;CACHE				;enable inst/data cache for fast memory with MMU
CACHECHIP			;enable inst cache for chip/fast memory
;CACHECHIPDATA			;enable inst/data cache for chip/fast memory
;DEBUG				;add more internal checks
;DISKSONBOOT			;insert disks in floppy drives
DOSASSIGN			;enable _dos_assign routine
;FONTHEIGHT	= 8		;enable 80 chars per line
HDINIT				;initialize filesystem handler
HRTMON				;add support for HrtMON
IOCACHE		= 1024		;cache for the filesystem handler (per fh)
;MEMFREE	= $200		;location to store free memory counter
;NEEDFPU			;set requirement for a fpu
POINTERTICKS	= 1		;set mouse speed
SEGTRACKER			;add segment tracker
SETKEYBOARD			;activate host keymap
SETPATCH			;enable patches from SetPatch 1.38
;SNOOPFS			;trace filesystem handler
;STACKSIZE	= 6000		;increase default stack
;TRDCHANGEDISK			;enable _trd_changedisk routine
WHDCTRL				;add WHDCtrl resident command

;============================================================================

slv_Version	= 17
slv_Flags	= WHDLF_NoError
slv_keyexit	= $59	;F10

;============================================================================

	INCLUDE	whdload/kick13.s

;============================================================================

slv_CurrentDir	dc.b	"data",0
slv_name	dc.b	"Legends Of Valour",0
slv_copy	dc.b	"1992 US-GOLD.",0
slv_info	dc.b	"Reworked by Vesuri",10
		dc.b	"based on the work of CFou!",10
		dc.b	"Version 2.0b (09.11.2026)",0
slv_config	dc.b	"C1:B:Character creation;"
	IFD DEVELOPER
		dc.b	"C2:X:faster chunky-to-planar:0;"
		dc.b	"C2:X:chunky buffer in public memory:1;"
		dc.b	"C2:X:unrolled wall columns:2;"
		dc.b	"C2:X:unrolled sprite columns:3;"
		dc.b	"C2:X:cached ray reciprocals:4;"
		dc.b	"C2:X:MOVEM chunky clear:5;"
		dc.b	"C2:X:Frame-independent game timing:6;"
		dc.b	"C2:X:One-degree mouse precision:7;"
		dc.b	"C2:X:Click inputs need a release:8;"
	ELSE
		dc.b	"C2:B:Enhanced frame rate;"
	ENDC
	IFD VERIFY
		dc.b	"C5:X:input tape from data/lovtape (verification):0;"
		dc.b	"C5:X:C2P pixel twin (verification):1;"
		dc.b	"C5:X:force chunky PUBLIC allocation failure (verification):2;"
		dc.b	"C5:X:chunky allocation/free cycle (verification):3;"
		dc.b	"C5:X:wall-column pixel/register twin (verification):4;"
		dc.b	"C5:X:sprite-column pixel/register twin (verification):5;"
		dc.b	"C5:X:ray reciprocal twin (verification):6;"
		dc.b	"C5:X:chunky-clear pixel/register twin (verification):7;"
	ENDC
		dc.b	0
	EVEN

;============================================================================
; like a program from "startup-sequence" executed, full dos process

_bootdos	lea	(_saveregs,pc),a0
		movem.l	d1-d3/d5-d7/a1-a2/a4-a6,(a0)
		move.l	(a7)+,(11*4,a0)
		move.l	(_resload,pc),a2	;A2 = resload

		lea	(_tag,pc),a0
		jsr	(resload_Control,a2)
	IFND DEVELOPER
	; Release builds: CUSTOM2 is the Enhanced frame rate switch. Any value selects every
	; enhancement (W1-W6, the 25 Hz game timing, mouse precision, click inputs), so the
	; 09.10.2026 icons' CUSTOM2=64 keeps them; 0 or no tooltype runs the original game.
	; Individual installers retain CPU selection and allocation fallback.
		lea	(_custom2,pc),a0
		tst.l	(a0)
		beq	.original
		move.l	#$1ff,(a0)
.original
	ENDC

	;open doslib
		lea	(_dosname,pc),a1
		move.l	(4),a6
		jsr	(_LVOOldOpenLibrary,a6)
		lea	(_dosbase,pc),a0
		move.l	d0,(a0)
		move.l	d0,a6			;A6 = dosbase

	;assigns
		lea	(_disk1,pc),a0
		sub.l	a1,a1
		bsr	_dos_assign

	;load exe: CUSTOM1 selects the character creation program
		lea	(_program,pc),a0
		move.l	(_custom1,pc),d0
		beq	.load
		lea	(_program2,pc),a0
.load		move.l	a0,d1
		jsr	(_LVOLoadSeg,a6)
		move.l	d0,d7			;D7 = segment
		beq	.program_err

	;set debug
		clr.l	-(a7)
		move.l	d7,-(a7)
		pea	WHDLTAG_DBGSEG_SET
		move.l	a7,a0
		jsr	(resload_Control,a2)
		add.w	#12,a7

	;patch: PowerPacker stub exit, or the program itself if not crunched
		move.l	d7,a1
		add.l	a1,a1
		add.l	a1,a1
		cmp.l	#$487a0178,(4,a1)	;stub: pea ($178,pc)
		bne	.unpacked
		pea	(_decrunched,pc)
		move.w	#$4ef9,($17a,a1)	;stub+$176: jmp _decrunched
		move.l	(a7)+,($17c,a1)
		cmp.w	#$33cb,($214,a1)	;stub+$210: move.w a3,$dff180
		bne	.patched
		move.w	#$6004,($214,a1)	;bra.s over the decrunch flash
		bra	.patched
.unpacked	lea	(4,a1),a0
		move.l	a0,d0
		bsr	_patchgame
.patched
	;call
		move.l	d7,d1
		moveq	#_args_end-_args,d0
		lea	(_args,pc),a0
		bsr	.call

		pea	TDREASON_OK
		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

.program_err	jsr	(_LVOIoErr,a6)
		pea	(_program,pc)
		move.l	d0,-(a7)
		pea	TDREASON_DOSREAD
		jmp	(resload_Abort,a2)

; D0 = ULONG arg length
; D1 = BPTR  segment
; A0 = CPTR  arg string

.call		lea	(_callregs,pc),a1
		movem.l	d2-d7/a2-a6,(a1)
		move.l	(a7)+,(11*4,a1)
		move.l	d0,d4
		lsl.l	#2,d1
		move.l	d1,a3
		move.l	a0,a4
	;create longword aligend copy of args
		lea	(_callargs,pc),a1
		move.l	a1,d2
.callca		move.b	(a0)+,(a1)+
		subq.w	#1,d0
		bne	.callca
	;set args
		move.l	(_dosbase,pc),a6
		jsr	(_LVOInput,a6)
		lsl.l	#2,d0		;BPTR -> APTR
		move.l	d0,a0
		lsr.l	#2,d2		;APTR -> BPTR
		move.l	d2,(fh_Buf,a0)
		clr.l	(fh_Pos,a0)
		move.l	d4,(fh_End,a0)
	;call
		move.l	d4,d0
		move.l	a4,a0
		movem.l	(_saveregs,pc),d1-d3/d5-d7/a1-a2/a4-a6
		jsr	(4,a3)
	;return
		movem.l	(_callregs,pc),d2-d7/a2-a6
		move.l	(_callrts,pc),a0
		jmp	(a0)

;============================================================================
; The stub's "movem.l (a7)+,d0-a6 / rts", replaced: (a7) is the entry of the loaded hunk 0
; and the restored registers are the program's startup registers, except D0/A0 (args).

_decrunched	movem.l	(a7)+,d0-a6
		move.l	(a7),d0

; D0 = APTR hunk 0.  Out: D0/A0 = args as passed to the program; all other registers kept.

_patchgame
		bsr	_map_hunks
		bsr	_lov_version
	IFD VERIFY
	; The VERIFY instruments can lie beyond BSR's reach: call them relatively.
		lea	(_patchgame,pc),a0
		adda.l	#_verify_ccr_install-_patchgame,a0
		jsr	(a0)
	ENDC
		move.l	(_hunks+4,pc),a0
		subq.l	#4,a0			;A0 = hunk 1 - 4
	;skip the manual protection, two AMIGA2 versions
		cmp.l	#$bc876656,($13e4,a0)	;h1:013e0 cmp.l d7,d6 / bne
		bne	.v2
		move.l	#$2e064e71,($13e4,a0)	;move.l d6,d7 / nop
		move.l	#$4e714e71,($1422,a0)
		move.w	#$4e71,($1426,a0)
.v2		cmp.l	#$bc876656,($13dc,a0)	;h1:013d8
		bne	.done
		move.l	#$2e064e71,($13dc,a0)
		move.l	#$4e714e71,($141a,a0)
		move.w	#$4e71,($141e,a0)
.done
	; Optional W1 hook, checked while disabled: PERF_RANGE h12:054ce 10
		bsr	_blit_install
		bsr	_c2p_install
		bsr	_w2_install
		bsr	_w3_install
		bsr	_w4_install
		bsr	_w5_install
		bsr	_w6_install
		bsr	_sim_install
		bsr	_turn_install
		bsr	_click_install
	IFD VERIFY
	IFD TIMING_STUDY
		bsr	_timing_study_install
	ENDC
		lea	(_patchgame,pc),a0
		adda.l	#_tape_install-_patchgame,a0
		jsr	(a0)
	ENDC
		moveq	#_args_end-_args,d0
		lea	(_args,pc),a0
		rts

; D0 = first hunk APTR. Shared by the normal patches and VERIFY tape.
; CHARACT has fewer hunks: stop at its null link and clear the remaining entries.
_map_hunks	movem.l	d1/a1,-(a7)
		lea	(_hunks,pc),a1
		moveq	#17-1,d1
.next		move.l	d0,(a1)+
		beq	.zero
		move.l	d0,a0
		move.l	(-4,a0),d0
		lsl.l	#2,d0
		beq	.zero
		addq.l	#4,d0
.zero		dbf	d1,.next
		movem.l	(a7)+,d1/a1
		rts

; Every enhancement patches game offsets, written as hN_OFFSET symbols (src/offsets.s); the
; slave is assembled for the English AMIGA2 of the 0837 archive and carries the German (0525)
; and French (1768) values as a fixup table. _lov_version recognises the AMIGA2 by its 17
; hunk sizes and applies the table for German or French. Any other AMIGA2 (CFou!'s v1.0 also
; supports another English one) runs with CUSTOM2 cleared, so no installer checks or writes
; it: the game runs as v1.0.
; The PowerPacker stub stores each hunk's allocation + 8 before its next-hunk link (the
; last hunk links to the stub's own segment, so the link does not end the list).
_lov_version	movem.l	d0-d2/a0-a3,-(a7)
		move.l	(_custom1,pc),d0
		bne	.done			;CHARACT has no enhancements
		lea	(_lov_version,pc),a3	;the tables are at the end of the slave
		adda.l	#_lov_hunk_sizes-_lov_version,a3
		moveq	#0,d2			;D2 = language
.lang		lea	(_hunks,pc),a0
		move.w	d2,d0
		mulu	#17*4,d0
		lea	(a3,d0.l),a1
		moveq	#17-1,d1
.next		move.l	(a0)+,d0
		beq	.other
		move.l	d0,a2
		move.l	(-8,a2),d0
		cmp.l	(a1)+,d0
		bne	.other
		dbf	d1,.next
		lea	(_lov_lang,pc),a0
		move.w	d2,(a0)
		beq	.done
		bsr	_lov_fixup
		bra	.done
.other		addq.w	#1,d2
		cmp.w	#3,d2
		bne	.lang
		lea	(_custom2,pc),a0
		clr.l	(a0)
.done		movem.l	(a7)+,d0-d2/a0-a3
		rts

; D2 = 1 German, 2 French: write that language's words of the fixup table over the
; English ones, then flush the caches.
_lov_fixup	movem.l	d0-d1/a0-a2,-(a7)
		lea	(_lov_fixup,pc),a0
		adda.l	#_lov_fixups-_lov_fixup,a0
		move.l	a0,a1
		suba.l	(a0)+,a1		;A1 = the slave's first byte
		move.l	(a0)+,d1		;entries
		bra	.go
.next		move.l	(a0)+,d0
		cmp.w	#1,d2
		beq	.de
		move.w	(2,a0),(0,a1,d0.l)
		bra	.step
.de		move.w	(a0),(0,a1,d0.l)
.step		addq.l	#4,a0
.go		subq.l	#1,d1
		bcc	.next
		move.l	(_resload,pc),a2
		jsr	(resload_FlushCache,a2)
		movem.l	(a7)+,d0-d1/a0-a2
		rts

_disk1		dc.b	"LOV",0		;for Assign
_program	dc.b	"AMIGA2",0
_program2	dc.b	"CHARACT",0
_args		dc.b	10		;must be LF terminated
_args_end
	EVEN

	CNOP 0,4
_tag		dc.l	WHDLTAG_CUSTOM1_GET
_custom1	dc.l	0
		dc.l	WHDLTAG_CUSTOM2_GET
_custom2	dc.l	0
		dc.l	WHDLTAG_ATTNFLAGS_GET
_lov_attnflags	dc.l	0
	IFD VERIFY
		dc.l	WHDLTAG_CUSTOM5_GET
_custom5	dc.l	0
	ENDC
		dc.l	TAG_DONE
_saveregs	ds.l	11
_saverts	dc.l	0
_dosbase	dc.l	0
_callregs	ds.l	11
_callrts	dc.l	0
_callargs	ds.b	208
_lov_lang	dc.w	0		;0 English, 1 German, 2 French
		CNOP	0,4
_hunks
_hunk0		dc.l	0
		ds.l	5
_h6		dc.l	0
		ds.l	4
_h11		dc.l	0
_h12		dc.l	0
		ds.l	4

		INCLUDE	blitwait.s
		INCLUDE	c2p.s
		INCLUDE	chunky.s
		INCLUDE	walls.s
		INCLUDE	sprites.s
		INCLUDE	rays.s
		INCLUDE	clear.s
		INCLUDE	simulation.s
		INCLUDE	turning.s
		INCLUDE	clicks.s

	IFD VERIFY
	IFD PROFILER_WINDOW
		INCLUDE	profile_window.s
	ENDC
	IFD TIMING_STUDY
		INCLUDE	timing_study.s
	ENDC
		INCLUDE	verify_flags.s
		INCLUDE	tape.s
	ENDC
	; Last: VERIFY builds use up the tag list's PC-relative reach before this point.
		INCLUDE	clicks_hooks.s

; _lov_version: allocation + 8 of hunks 0-16 of the English, German and French AMIGA2
; (tools/unpack.py; docs/profiling.md §2).
		CNOP	0,4
	IFD VERIFY_FOREIGN_VERSION
	; VERIFY: one size off, so the English AMIGA2 runs as an unrecognised version.
_lov_hunk_sizes	dc.l	$199c+8+4,$2c2c+8,$63fc+8,$5bc+8,$b0+8,$2700+8,$8f0+8,$2d8+8
	ELSE
_lov_hunk_sizes	dc.l	$199c+8,$2c2c+8,$63fc+8,$5bc+8,$b0+8,$2700+8,$8f0+8,$2d8+8
	ENDC
		dc.l	$850+8,$660+8,$c4+8,$a4dc+8,$179d0+8,$14+8,$ec+8,$184+8,$dc+8
		dc.l	$199c+8,$2c2c+8,$640c+8,$5bc+8,$b0+8,$2700+8,$8f0+8,$2d8+8	;German
		dc.l	$850+8,$660+8,$c4+8,$a4e0+8,$17a4c+8,$14+8,$ec+8,$184+8,$dc+8
		dc.l	$199c+8,$2c34+8,$640c+8,$5bc+8,$b0+8,$2700+8,$8f0+8,$2d8+8	;French
		dc.l	$850+8,$660+8,$c4+8,$a4dc+8,$17a4c+8,$14+8,$ec+8,$184+8,$dc+8

;============================================================================

		CNOP 0,4
_c2p_edges	ds.b	4*92*4
	IFD VERIFY
		CNOP 0,4
_c2p_scratch	ds.b	4*40*92
	ENDC
		CNOP 0,4
_c2p_chunky
	IFD VERIFY
		ds.b	20000	;W6 compares the full allocation using this staging area
	ELSE
		ds.b	192*92
	ENDC

;============================================================================

        CNOP 0,4
_sim_input_ring ds.b SIM_INPUT_SLOTS*SIM_INPUT_STRIDE
	IFD SIM_COMBAT_EXPERIMENT
_sim_combat_ring ds.b 512*12
	ENDC

	IFD VERIFY
	IFD SIM_KEYBOARD_EXPERIMENT
_sim_keys_readlog ds.b 64*12
	ENDC
	IFD TIMING_STUDY
_timing_combat_records ds.b 64*32
	IFD SIM_COMBAT_EXPERIMENT
_timing_combat_clock_records ds.b 64*20
	ENDC
	ENDC
	ENDC

; Last before the fixup table, so no code or data offset moves; the version and date match
; slv_info and the release ReadMe.
		dc.b	"$VER: LegendsOfValour.Slave 2.0b (09.11.2026)",0

; The fixup table is after it, the very last: it is appended to the English build without
; moving anything (game.sh, tools/fixups.py).
		CNOP	0,4
	IFD LOV_PASS1
_lov_fixups	dc.l	0,0
	ELSE
		INCLUDE	lov_fixups.s
	ENDC

	END
