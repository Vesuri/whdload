; F4: the log conversion's leading-bit search with BFFFO (68020+).
; Replaces Disk.1 $4EE88..$4EF91 in M1's copy, which keeps the $4EE76 word entry
; ($4EE82's bra.s retargets to _f4word) and the $4EE84 long entry before it.
; Returns the original d1 (exponent:mantissa*2, signed), d6 (input), d7 (exponent;
; its high word is preserved below $10000, as the original's clr.w d7) and flags.
; tools/log_harness.py compares it with the original for every input.
_f4code
	move.l	d1,d6
	bpl.b	_f4abs
	neg.l	d1
_f4abs	beq.b	_f4zero
	cmpi.l	#$10000,d1
	blo.b	_f4word
	bfffo	d1{0:16},d7		;leading zeros c, 0..15
	lsl.l	d7,d1
	eori.w	#31,d7			;exponent 31-c
	lsr.l	#4,d1			;high word: the top 12 bits
	move.w	d7,d1
	swap	d1
	bra.b	_f4sign
_f4word	move.w	d1,d7			;below $10000: d7 = preserved word:input
	bfffo	d1{16:16},d1		;16+c
	rol.w	d1,d7			;input<<c (rotates by c, without wrap)
	lsr.w	#4,d7
	eori.w	#31,d1			;exponent 15-c
	swap	d1
	move.w	d7,d1
	swap	d1
	move.w	d1,d7
	swap	d1
_f4sign	add.w	d1,d1
	tst.l	d6
	bpl.b	_f4done
	neg.w	d1
_f4done	rts
_f4zero	move.l	#$fff01000,d1
	rts
_f4end
