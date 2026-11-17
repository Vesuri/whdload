		incdir	"include:"
		include	whdload.i
		opt	o4-		; the shipped slave keeps move.l #65536,d0, not moveq+swap

_base		SLAVE_HEADER			;ws_Security + ws_ID
		dc.w	10			;ws_Version
		dc.w	WHDLF_NoError|WHDLF_EmulTrap|WHDLF_NoKbd
		dc.l	$80000			;ws_BaseMemSize
		dc.l	0			;ws_ExecInstall
		dc.w	Start-_base		;ws_GameLoader
		dc.w	_data-_base
		dc.w	0			;ws_DontCache
_keydebug	dc.b	0			;ws_keydebug
_keyexit	dc.b	$59			;ws_keyexit = F10
_expmem		dc.l	0
		dc.w	_name-_base		;ws_name
		dc.w	_copy-_base		;ws_copy
		dc.w	_info-_base		;ws_info
_data		dc.b	"data",0
_name		dc.b	"Zany Golf",0
_copy		dc.b	"1988 Electronic Arts",0
_info		dc.b	"installed & fixed by Bored Seal",10
		dc.b	"V1.1 (23-Jul-2006)",0
		even

Start		lea	_resload(pc),a1
		move.l	a0,(a1)
		move.l	a0,a2

		lea	(_OSEmu,pc),a0	;load&init the osemu module
		lea	($400).w,a3
		move.l	a3,a1
		jsr	(resload_LoadFileDecrunch,a2)
		move.l	a2,a0
		lea	(_base,pc),a1
		jsr	(a3)
		move.w	#0,sr

		lea	dosname,a1
		clr.l	d0
		movea.l	4,a6
		jsr	-$228(a6)
		move.l	d0,a6

		lea	file,a0
		move.l	a0,d1
		jsr	-150(a6)

		add.l	d0,d0
		add.l	d0,d0
		addq.l	#4,d0
		move.l	d0,a1

		sub.l	a0,a0
		moveq.l	#0,d0

		move.w	#$6002,$48(a1)		;deprotect
		move.b	#$60,$5a(a1)

		move.w	#$4e75,$62e(a1)		;disk access

		move.w	#$4ef9,$658(a1)
		pea	Patch
		move.l	(sp)+,$65a(a1)
		jmp	(a1)

Patch		movem.l	d0-d7/a0-a6,-(sp)
		move.l	a3,a0
		move.l	#65536,d0
		move.l	(_resload,pc),a2
		jsr     (resload_CRC16,a2)
		cmpi.w	#$9cc8,d0	; cmpi as the shipped slave has it: vasm encodes cmp #,Dn as CMP
		bne	Unsupported

		move.l	#$4e714eb9,$1f38(a3)	;fix keyboard and set cheat
		pea	FixKey
		move.l	(sp)+,$1f3c(a3)

		move.w	#$4eb9,$14a4(a3)	;the renderer's flip: at most one frame
		pea	FrameCap		;each FRAME_FIELDS fields
		move.l	(sp)+,$14a6(a3)
		move.w	#$4e71,$14aa(a3)

		move.l	#$01384ef9,$5238(a3)	;the main loop: step the world each
		pea	Split			;STEP_FIELDS fields, draw in between
		move.l	(sp)+,$523c(a3)

		movem.l	(sp)+,d0-d7/a0-a6
		jmp	(a3)

; The game advanced its world one step a drawn frame and counts the step as 6 fields
; (10 steps a second at NTSC). Split (below) now steps the world on its own clock, so
; this only keeps the flips to at most one a field. Replaces the flip's first two
; instructions (FILE1 $14a4: the fine scroll into the copper list, and d0 = $8000) and
; first waits until FRAME_FIELDS fields have passed since the previous flip, by the game's
; field counter (FILE1 $145c, low byte). The counter advances at the copper interrupt
; (line $90), after the copper has loaded the field's plane pointers, so a flip there
; shows from the top of the next field. No wait while the interrupts are off (the counter
; would not move). a4 is FILE1's base here.
FRAME_FIELDS	= 1
FrameCap	move.w	d0,$2312(a4)		;displaced: the fine scroll
		movem.l	d1/a0,-(sp)
		lea	(_lastflip,pc),a0
		move.w	$dff01c,d1		;INTENAR: master, COPER and VERTB on?
		and.w	#$4030,d1
		cmp.w	#$4030,d1
		bne.b	.go
.wait		move.b	$145c(a4),d1
		sub.b	(a0),d1
		cmp.b	#FRAME_FIELDS,d1
		bcs.b	.wait
.go		move.b	$145c(a4),(a0)
		movem.l	(sp)+,d1/a0
		move.w	#$8000,d0		;displaced
		rts

_lastflip	dc.b	0
		even

; The main loop (FILE1 $5232, threaded code) draws a frame when the drawing flag ($0ea0)
; is set (JSR $4fd0, $1478, $48d4), then reads the input (JSR $1d5a) and steps the world
; (JSR $62b2, which also adds 6 fields to the game clock). Replaces the flag test at $5238
; (LDA $0ea0; BEQ $524c) with native code (primitive $0138) that jumps here and picks the
; rest of the pass by setting the thread pointer a5:
; - flag clear: input and step ($524c), and loop; the game clock then counts real fields.
; - flag set and STEP_FIELDS fields since the last step: the same, input and step only, so
;   the step is not held up behind a frame; the next pass draws it.
; - flag set and fewer: draw only (DrawOnly), and loop.
; A step can change the flag (the pause screen clears it), and the next pass tests it again,
; as the game's own next pass did.
; Steps are due every STEP_FIELDS fields by the field counter; a step more than one step
; late restarts the schedule from now, so a slow machine steps every pass as before and
; never catches up in a burst. With the interrupts off the counter stops, so every pass
; steps. a4 is FILE1's base, d7 and a0 are scratch in the threaded code.
STEP_FIELDS	= 6
Split		move.b	$0ea0(a4),d0		;displaced: LDA $0ea0
		move.b	d0,d4
		lea	(_laststep,pc),a0
		beq.b	.update
		move.w	$dff01c,d7		;INTENAR: master, COPER and VERTB on?
		and.w	#$4030,d7
		cmp.w	#$4030,d7
		bne.b	.step
		move.b	$145c(a4),d7
		sub.b	(a0),d7
		cmp.b	#STEP_FIELDS,d7
		bcs.b	.draw
		cmp.b	#2*STEP_FIELDS,d7
		bcc.b	.late
		addq.b	#STEP_FIELDS,(a0)
		bra.b	.step
.late		move.b	$145c(a4),(a0)
.step		lea	$524c(a4),a5		;JSR $1d5a; JSR $62b2; JMP $5232
		jmp	$0122(a4)		;dispatch
.draw		lea	(DrawOnly,pc),a5
		jmp	$0122(a4)
.update		move.b	$145c(a4),d7		;the first pass with the flag set steps
		subq.b	#STEP_FIELDS,d7
		move.b	d7,(a0)
		bra.b	.step

DrawOnly	dc.w	$05e8,$4fd0		;JSR $4fd0
		dc.w	$05e8,$1478		;JSR $1478: the renderer
		dc.w	$05e8,$48d4		;JSR $48d4
		dc.w	$0438,$5232		;JMP $5232

_laststep	dc.b	0
		even

FixKey		move.w	4(sp),d0
		ror.b	#1,d0
		not.b	d0
		cmpi.b	#$59,d0		; cmpi as the shipped slave has it: vasm encodes cmp #,Dn as CMP
		bne	BeamDelay
		move.b	#9,$15ca2	;set 9 strokes
BeamDelay	moveq	#8,d0
BM_1		move.w  d0,-(sp)
		move.b	$dff006,d0
BM_2		cmp.b	$dff006,d0
		beq	BM_2
		move.w	(sp)+,d0
		dbf	d0,BM_1
		rts

Unsupported	pea	TDREASON_WRONGVER
_end		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

_resload	dc.l	0		;address of resident loader
_OSEmu		dc.b	'osemu.400',0
file		dc.b	"zany",0
dosname		dc.b	"dos.library",0