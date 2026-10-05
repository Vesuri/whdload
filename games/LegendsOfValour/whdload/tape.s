;*---------------------------------------------------------------------------
; VERIFY-only scripted mouse input ("input tape"), enabled by CUSTOM5 bit 0.
;
; The game takes its pointer position from its intuition window: h1:01b8c copies
; Window->MouseX/MouseY ($e/$c of the window at h11:05eb0, -8528(a4)) on every poll.  Buttons
; come from the hardware: the vertical-blank server (h12:06404) calls h12:05298, which
; debounces CIAAPRA bit 6 / POTINP bit 10 into h12:05292 (bit 0 left, bit 1 right).  (The
; server's JOY0DAT accumulators h11:008d2/008d4 are relative mouse-look deltas; untouched.)
; With the tape on, h12:05298 jumps here instead: every field the current entry's position
; is written into the window and its buttons into h12:05292, then the entry's field count
; advances.  Run with JOY0=none: no mouse events, so intuition never rewrites MouseX/Y.  The
; visible (intuition) pointer sprite does not follow the tape.
;
; Tape file data/lovtape (tools/tape.py builds it), big-endian words, entries of 8 bytes:
;	dc.w	fields,x,y,buttons	; hold for FIELDS fields; FIELDS=0 holds forever
; Field 0 of the tape is the first call of the server after the game installs it.
;---------------------------------------------------------------------------*

TAPEMAX		= 8192			;bytes

; called from _patchgame with the program loaded, before it runs; keeps all registers
; except D0/A0
_tape_install	move.l	(_custom5,pc),d0
		btst	#0,d0
		beq	.off
		movem.l	d1-d2/a1-a2,-(a7)
	;hunk addresses: follow the segment chain from hunk 0
		move.l	(_hunk0,pc),a0
		moveq	#11-1,d1
.h11		move.l	(-4,a0),d0
		lsl.l	#2,d0
		move.l	d0,a0
		addq.l	#4,a0
		dbf	d1,.h11
		lea	(_h11,pc),a1
		move.l	a0,(a1)
		move.l	(-4,a0),d0
		lsl.l	#2,d0
		move.l	d0,a0
		addq.l	#4,a0
		lea	(_h12,pc),a1
		move.l	a0,(a1)
	;check the bytes replaced: moveq #0,d0 / btst #6,$bfe001
		cmp.l	#$70000839,($5298,a0)
		bne	.bad
		cmp.l	#$000600bf,($529c,a0)
		bne	.bad
	;load the tape
		lea	(_tapename,pc),a0
		lea	(_tape,pc),a1
		move.l	(_resload,pc),a2
		jsr	(resload_LoadFile,a2)
		cmp.l	#TAPEMAX,d0
		bhi	.bad
		lea	(_tapeptr,pc),a0
		lea	(_tape,pc),a1
		move.l	a1,(a0)
	;h12:05298: jmp _tape_vbl
		move.l	(_h12,pc),a0
		move.w	#$4ef9,($5298,a0)
		pea	(_tape_vbl,pc)
		move.l	(a7)+,($529a,a0)
		move.l	(_resload,pc),a2
		jsr	(resload_FlushCache,a2)
		movem.l	(a7)+,d1-d2/a1-a2
.off		rts
.bad		pea	(_tapebad,pc)
		pea	TDREASON_FAILMSG
		move.l	(_resload,pc),a2
		jmp	(resload_Abort,a2)

; replaces h12:05298 (bsr from the VBL server, which saved d0-a6 around the call)
_tape_vbl	move.l	(_tapeptr,pc),a1
		move.l	(_h11,pc),a0
		move.l	($5eb0,a0),d0		;the game's window
		beq	.nowin
		move.l	d0,a0
		move.w	(2,a1),($e,a0)		;wd_MouseX
		move.w	(4,a1),($c,a0)		;wd_MouseY
.nowin
		move.l	(_h12,pc),a0
		move.w	(6,a1),($5292,a0)
		move.w	(a1),d0
		beq	.hold
		lea	(_tapecnt,pc),a0
		addq.w	#1,(a0)
		cmp.w	(a0),d0
		bhi	.hold
		clr.w	(a0)
		lea	(_tapeptr,pc),a0
		addq.l	#8,(a0)
.hold		lea	(_tapefield,pc),a0
		addq.l	#1,(a0)
		moveq	#0,d0
		rts

_tapename	dc.b	"lovtape",0
_tapebad	dc.b	"input tape: unexpected game code or tape too large",0
	EVEN
	CNOP 0,4
_hunk0		dc.l	0
_h11		dc.l	0
_h12		dc.l	0
_tapeptr	dc.l	0
_tapefield	dc.l	0		;fields since the tape started (for debugging)
_tapecnt	dc.w	0
	EVEN
_tape		ds.b	TAPEMAX
