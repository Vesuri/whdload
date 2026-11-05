from pathlib import Path
r=Path('src');p=r/'HardDrivinDecay.s';Path('tmp/p4-before/HardDrivinDecay.s').write_bytes(p.read_bytes())
p=r/'HardDrivinTime.s';s=p.read_text();s=s.replace('\tbsr _dispatch_begin\n\tENDC\n\tIFND VERIFY_TIME_DISPATCH','\tbsr _dispatch_begin\n\tENDC\n\tIFD VERIFY_TIME_SCALARS\n\tbsr _time_prepare_constants\n\tENDC\n\tIFND VERIFY_TIME_DISPATCH',1)
a=s.index('\n_time_pause:');block='''
	IFD VERIFY_TIME_SCALARS
; Cache by actual scalar interval. Native engine endpoints temporarily use n=8,
; off-road phase decay uses PH_DT, and a later dispatcher substep may differ.
; Consumers compare their own n before using a coefficient; mismatches keep
; the original tables. Initialize the sentinel interval65535 with exact values.
FC_PLUS equ 4
FC_MINUS equ 8
FC_T equ 12
FC_THROTTLE equ 16
FC_SPIN equ 20
FC_CONTACT equ 24
FC_RETAIN equ 28
FC_RATE equ 32
_time_frame_constants:
	dc.w 65535,0
	dc.l 65543,-65527,$1fffe000,65536,65536,65536,0,8
_time_prepare_constants:
	moveq #0,d0
	move.w _time_scalar_fields(pc),d0
	cmp.w _time_frame_constants(pc),d0
	beq.s .done
	lea _time_frame_constants(pc),a1
	move.l d0,d1
	addq.l #8,d1
	move.l d1,FC_PLUS(a1)
	moveq #8,d1
	sub.l d0,d1
	move.l d1,FC_MINUS(a1)
	move.l d0,d1
	lsl.l #8,d1
	lsl.l #5,d1
	move.l d1,FC_T(a1)
	move.w d0,d1
	bsr _decay_throttle
	move.l d1,FC_THROTTLE(a1)
	move.w d0,d1
	bsr _decay_spin
	move.l d1,FC_SPIN(a1)
	move.w d0,d1
	bsr _decay_contact
	move.l d1,FC_CONTACT(a1)
	neg.l d1
	addi.l #65536,d1
	move.l d1,FC_RETAIN(a1)
	IFD VERIFY_TIME_MOTION
	cmpi.w #8,d0
	bls.s .short_rate
	; Same independently rounded Gain/T as _contact_response's wide path.
	move.l FC_CONTACT(a1),d1
	lsl.l #3,d1
	move.l d0,-(a7)
	lsr.l #1,d0
	add.l d0,d1
	move.l (a7)+,d0
	divu.w d0,d1
	andi.l #$ffff,d1
	bra.s .rate_ready
.short_rate:
	move.l a0,-(a7)
	lea _contact_rate_gain(pc),a0
	move.w d0,d1
	add.w d1,d1
	move.w (a0,d1.w),d1
	andi.l #$ffff,d1
	movea.l (a7)+,a0
.rate_ready:
	move.l d1,FC_RATE(a1)
	ENDC
	; Publish the key last: table routines must not read half-updated data.
	move.w d0,(a1)
.done:
	rts
	ENDC
''';s=s[:a]+block+s[a:];s=s.replace('\tbeq.s .done\n\tlea _time_frame_constants','\tbeq .done\n\tlea _time_frame_constants',1);p.write_text(s)
p=r/'HardDrivinDecay.s';s=p.read_text()
for n,off in [('throttle','FC_THROTTLE'),('spin','FC_SPIN'),('contact','FC_CONTACT')]:
 s=s.replace(f'_decay_{n}:\n',f'''_decay_{n}:
	cmp.w _time_frame_constants(pc),d1
	bne.s .table
	move.l _time_frame_constants+{off}(pc),d1
	rts
.table:
''',1)
p.write_text(s)
p=r/'HardDrivinContact.s';s=p.read_text();s=s.replace('.feedback:\n\t; Round Gain/T', '''.feedback:
	cmp.w _time_frame_constants(pc),d4
	bne.s .rate_uncached
	move.l _time_frame_constants+FC_RATE(pc),d1
	bra.s .rate_ready
.rate_uncached:
	; Round Gain/T''',1).replace('\tdivu.w d4,d1\n\tmuls.w d1,d3','\tdivu.w d4,d1\n.rate_ready:\n\tmuls.w d1,d3',1);p.write_text(s)
