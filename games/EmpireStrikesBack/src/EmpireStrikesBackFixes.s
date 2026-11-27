; Fixes for fast CPUs, always applied. Addresses are the game's ($500 + image offset).
;
; Timing. Every scene ends its frame in the swap at $5dc02, which clears INTREQ's COPER
; bit and waits for the copper to set it again at line $e0: one field at least, and no
; other pacing. The game moves by the frame, so its speed followed the CPU: an A500 plays
; at 2 to 7 fields a frame (mostly 3 or 4) and the wave select at 3, a 68060 at 1. The
; swap now waits until three fields have passed since the last swap (at most 16.7 frames
; a second, PAL), as the Star Wars timing fix does; frames that take longer are not
; delayed. The fields are counted in the VBL server, at its call of the music player.

FixVblCount	lea	_FixFields(pc),a0	; the server saved every register
		addq.w	#1,(a0)
		jmp	$52690			; the original call, returns to the VBL server

; In: nothing; out: d0, a0 trashed (the original leaves them so too).
FixSwapWait	lea	$dff000,a0
.Field		move.w	#$10,$9c(a0)		; clear COPER, wait for line $e0
.Coper		btst	#4,$1f(a0)
		beq.b	.Coper
		move.w	_FixFields(pc),d0
		sub.w	_FixLast(pc),d0
		cmpi.w	#3,d0
		blo.b	.Field
		move.w	_FixFields(pc),d0
		lea	_FixLast(pc),a0
		move.w	d0,(a0)
		rts

_FixFields	dc.w	0
_FixLast	dc.w	0
