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
; buttons: bit 0 left, bit 1 right, bit 15 anchor (the entry's first field runs _tape_anchor),
; bit 14 (W): hold until the last hit-tested list has a button with id FIELDS
; (0: any) containing (x,y), instead of counting fields.
; Bit 12 (D, with anchor): TIMING_STUDY drawing delay, selected at the anchor.
; Bit 13 (H, with bit 14): wait for heading h11:08c28 to equal FIELDS instead.
; The game hit-tests its current
; screen's list through h6:0076c (entries: next, id, x, y, w, h longs), which the tape hooks to
; remember the list; it is forgotten every field, so only a list in use counts.
; Field 0 of the tape is the first call of the server after the game installs it.
;---------------------------------------------------------------------------*

TAPEMAX		= 8192			;bytes

; called from _patchgame with the program loaded, before it runs; keeps all registers
; except D0/A0
_tape_install	move.l	(_custom5,pc),d0
		lea	(_tape_custom5,pc),a0	;for code beyond the tag list's reach
		move.l	d0,(a0)
		btst	#0,d0
		beq	.off
		movem.l	d1-d2/a1-a2,-(a7)
		move.l	(_h12,pc),a0
	;check the bytes replaced: moveq #0,d0 / btst #6,$bfe001
		cmp.l	#$70000839,(h12_05298,a0)
		bne	.bad
		cmp.l	#$000600bf,(h12_0529c,a0)
		bne	.bad
		move.l	(_h6,pc),a0
		cmp.l	#$bfec0000+((h11_05e40-$8000)&$ffff),(h6_0076c,a0)	;cmpa.l -8640(a4),sp / bcs.w
		bne	.bad
		cmp.l	#$6500015e,(h6_00770,a0)
		bne	.bad
	;load the tape
		lea	(_tapename,pc),a0
		lea	(_tape,pc),a1

        lea (_tape_install,pc),a2
        adda.l #_resload-_tape_install,a2
        move.l (a2),a2
		jsr	(resload_LoadFile,a2)
		cmp.l	#TAPEMAX,d0
		bhi	.bad
		lea	(_tapeptr,pc),a0
		lea	(_tape,pc),a1
		move.l	a1,(a0)
	;h12:05298: jmp _tape_vbl
		move.l	(_h12,pc),a0
		move.w	#$4ef9,(h12_05298,a0)
		pea	(_tape_vbl,pc)
		move.l	(a7)+,(h12_0529a,a0)
	;h6:0076c: jmp _tape_hit
		move.l	(_h6,pc),a0
		move.w	#$4ef9,(h6_0076c,a0)
		pea	(_tape_hit,pc)
		move.l	(a7)+,(h6_0076e,a0)

        lea (_tape_install,pc),a2
        adda.l #_resload-_tape_install,a2
        move.l (a2),a2
		jsr	(resload_FlushCache,a2)
		movem.l	(a7)+,d1-d2/a1-a2
.off		rts
.bad		pea	(_tapebad,pc)
		pea	TDREASON_FAILMSG

        lea (_tape_install,pc),a2
        adda.l #_resload-_tape_install,a2
        move.l (a2),a2
		jmp	(resload_Abort,a2)

; replaces h12:05298 (bsr from the VBL server, which saved d0-a6 around the call)
_tape_vbl	move.l	(_tapeptr,pc),a1
		move.l	(_h11,pc),a0
		move.l	(h11_05eb0,a0),d0		;the game's window
		beq	.nowin
		move.l	d0,a0
		move.w	(2,a1),($e,a0)		;wd_MouseX
		move.w	(4,a1),($c,a0)		;wd_MouseY
.nowin
		move.l	(_h12,pc),a0
		move.w	(6,a1),d0
		and.w	#3,d0
		move.w	d0,(h12_05292,a0)
		btst	#6,(6,a1)
		bne	_tw_wait
		move.w	(a1),d0
		beq	_tape_next
		lea	(_tapecnt,pc),a0
		addq.w	#1,(a0)
		cmp.w	(a0),d0
		bhi	_tape_next
		clr.w	(a0)
		lea	(_tapeptr,pc),a0
		addq.l	#8,(a0)
		move.l	(a0),a0
		tst.w	(6,a0)
		bpl	_tape_next
_tape_anchor
	IFD TIMING_STUDY
        move.l (_tapeptr,pc),a0
        move.w (6,a0),d0
        and.w #$1000,d0
        lea (_timing_study_tape_delay,pc),a0
        move.w d0,(a0)
		lea (_timing_study_pending,pc),a0
		move.w #1,(a0)
	ENDC
	IFD PROFILER_WINDOW
		bsr _profile_prepare
_profile_ready	bsr _profile_restore
_profile_restored nop
	ELSE
		nop			;an entry marked A begins
	ENDC
_tape_next
	IFD TIMING_STUDY
        bsr _timing_study_wait_ready
        bsr _timing_study_input
	ENDC
        lea (_tapefield,pc),a0
		addq.l	#1,(a0)
		lea	(_tapelist,pc),a0
		clr.l	(a0)
		moveq	#0,d0
		rts

; wait entry: look for button id (a1) at (2,a1)/(4,a1) in the last hit-tested list
_tw_wait	btst	#5,(6,a1)		;H: wait for a heading, not a button
		bne	_tw_heading
	IFD VERIFY_WAIT_RESCUE
		bsr	_tw_rescue
		tst.w	d0
		bne	_tape_next
	ENDC
		move.l	(_tapelist,pc),d0
		moveq	#64-1,d1
_tw_node	btst	#0,d0
		bne	_tape_next
		tst.l	d0
		beq	_tape_next
		move.l	d0,a0
		move.w	(a1),d0
		beq	_tw_anyid
		ext.l	d0
		cmp.l	(4,a0),d0
		bne	_tw_skip
_tw_anyid	move.w	(2,a1),d0
		ext.l	d0
		sub.l	(8,a0),d0
		bmi	_tw_skip
		cmp.l	(16,a0),d0
		bgt	_tw_skip
		move.w	(4,a1),d0
		ext.l	d0
		sub.l	(12,a0),d0
		bmi	_tw_skip
		cmp.l	(20,a0),d0
		bgt	_tw_skip
	;found: next entry
_tw_advance
	IFD VERIFY_WAIT_RESCUE
		lea	(_tw_watch_fields,pc),a0
		clr.w	(a0)
	ENDC
		lea	(_tapecnt,pc),a0
		clr.w	(a0)
		lea	(_tapeptr,pc),a0
		addq.l	#8,(a0)
		move.l	(a0),a0
		tst.w	(6,a0)
		bmi	_tape_anchor
		bra	_tape_next
_tw_skip	move.l	(a0),d0
		dbf	d1,_tw_node
		bra	_tape_next

	IFD VERIFY_WAIT_RESCUE
; Slow C2P twin runs can leave another panel active during a later W wait.
; Pulse the EXIT/status-bar point only while waiting for the computer button.
; This fixture is excluded from ordinary VERIFY and performance captures.
_tw_rescue
		move.l	(_tape_custom5,pc),d0
		btst	#1,d0
		beq	.no
		tst.w	(a1)
		bne	.no
		cmp.w	#15,(2,a1)
		bne	.no
		cmp.w	#188,(4,a1)
		bne	.no
		lea	(_tw_watch_fields,pc),a0
		addq.w	#1,(a0)
		cmp.w	#100,(a0)
		blo	.no
		cmp.w	#180,(a0)
		bhs	.reset
		move.l	(_h11,pc),a0
		move.l	(h11_05eb0,a0),d0
		beq	.no
		move.l	d0,a0
		move.w	#75,($e,a0)
		move.w	#183,($c,a0)
		move.l	(_h12,pc),a0
		move.w	#1,(h12_05292,a0)
		moveq	#1,d0
		rts
.reset	clr.w	(a0)
.no		moveq	#0,d0
		rts
_tw_watch_fields dc.w 0
	ENDC
		CNOP	0,4
_tape_custom5	dc.l	0

; H entry: read game state, then release the turn input when the target is reached.
; The normal count path (including performance windows) has no additional work.
_tw_heading
        IFD TIMING_STUDY
        ; A fixed tick rate can bring the greeting into an H wait. Pulse EXIT
        ; while paused, then resume the tape's held turn. Verification only.
        move.l (_h12,pc),a0
        move.l a0,a2
        adda.l #h12_0a0c3,a0
        tst.b (a0)
        bne .heading_live
        move.l (_h11,pc),a0
        move.l (h11_05eb0,a0),d0
        beq _tape_next
        move.l d0,a0
        move.w #75,($e,a0)
        move.w #183,($c,a0)
        move.l (_tapefield,pc),d0
        and.w #63,d0
        cmp.w #48,d0
        scs d0
        not.b d0
        and.w #1,d0
        move.w d0,(h12_05292,a2)
        bra _tape_next
.heading_live
        ENDC
        move.l (_h11,pc),a0
		add.l	#h11_08c28,a0
		move.w	(a0),d0
		cmp.w	(a1),d0
		bne	_tape_next
		bra	_tw_advance

; replaces h6:0076c, the game's button hit test (list,x,y): remember the list
_tape_hit	move.l	a0,-(a7)
		lea	(_tapelist,pc),a0
		move.l	(8,a7),(a0)
		move.l	(a7)+,a0
		cmpa.l	(h11_05e40-$8000,a4),a7
		bcs	.ovf
		move.l	(_h6,pc),-(a7)
		add.l	#h6_00774,(a7)
		rts
.ovf		move.l	(_h6,pc),-(a7)		;stack overflow
		add.l	#h6_008d0,(a7)
		rts

_tapename	dc.b	"lovtape",0
_tapebad	dc.b	"input tape: unexpected game code or tape too large",0
	EVEN
	CNOP 0,4
_tapeptr	dc.l	0
_tapelist	dc.l	0		;button list of the last hit test (cleared every field)
_tapefield	dc.l	0		;fields since the tape started (for debugging)
_tapecnt	dc.w	0
	EVEN
_tape		ds.b	TAPEMAX
