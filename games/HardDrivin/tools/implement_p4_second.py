from pathlib import Path
r=Path('src');backup=Path('tmp/p4-before')
for name in ['HardDrivinContact.s','HardDrivinMotion.s']:
 p=r/name;(backup/name).write_bytes(p.read_bytes())
p=r/'HardDrivinTime.s';s=p.read_text().replace('_time_product_s32_u16:\n\tmovem.l', '''_time_product_s32_u16:
	; Exact zero product; common for grounded fall and angular rates.
	tst.l d0
	bne.s .multiply
	moveq #0,d2
	rts
.multiply:
	movem.l''',1);p.write_text(s)
p=r/'HardDrivinProjection.s';s=p.read_text().replace('\tmove.w d2,d1\n\tmuls.w -$6bb4(a4),d1','''	; Flat pitch has exact sine0/cosine16384. Avoid its two multiply/shift
	; pairs without approximating orientation or changing native word wrap.
	tst.w -$6bb4(a4)
	bne.s .pitch
	cmpi.w #16384,-$6bb2(a4)
	bne.s .pitch
	moveq #0,d1
	moveq #14,d4
	bra.s .yaw
.pitch:
	move.w d2,d1
	muls.w -$6bb4(a4),d1''',1).replace('\tasr.l d4,d2\n\tmove.w d2,d0','\tasr.l d4,d2\n.yaw:\n\tmove.w d2,d0',1);p.write_text(s)
p=r/'HardDrivinContact.s';s=p.read_text().replace('_contact_integrate_rate:\n\tmovem.l','''_contact_integrate_rate:
	; With zero rate/carry and an already canonical angle the result is
	; unchanged, even after a stale LAST value. Publish LAST as usual.
	tst.l d0
	bne.s .integrate
	tst.l (a0)
	bne.s .integrate
	cmpi.w #720,(a1)
	bgt.s .integrate
	cmpi.w #-720,(a1)
	blt.s .integrate
	move.w (a1),4(a0)
	; Preserve even the historical scratch result: wide returns the angle,
	; short returns a zero integer increment. No caller needs new semantics.
	move.l d1,-(a7)
	move.w _time_scalar_fields(pc),d1
	cmpi.w #8,d1
	bls.s .zero_done
	move.w (a1),d0
	ext.l d0
.zero_done:
	move.l (a7)+,d1
	rts
.integrate:
	movem.l''',1);p.write_text(s)
p=r/'HardDrivinPhase.s';s=p.read_text();a=s.index('_phase_gear:');b=s.index(' ; Skids retain',a);v=s[a:b].replace('d0-d7/a0-a2','d0-d5/a0/a2').replace('46(a7)','34(a7)');v=v.replace('_phase_gear:\n','_phase_gear:\n ; Scalar kernel clobbers only D0-D5/A0/A2; saved X follows eight registers.\n',1);s=s[:a]+v+s[b:]
s=s.replace(' bra _phase_project\n',' bra _phase_project_core\n',1).replace(' bsr _phase_project\n',' bsr _phase_project_core\n',1)
s=s.replace('_phase_project:\n movem.l d0-d7/a0-a1,-(a7)\n suba.w #12,a7','''_phase_project:
 movem.l d0-d7/a0-a1,-(a7)
 bsr _phase_project_core
 movem.l (a7)+,d0-d7/a0-a1
 rts
; Both runtime callers already preserve the outer frame's registers. The core
; clobbers D0-D2/D4-D7/A0-A1; A2-A6 and D3 are untouched.
_phase_project_core:
 suba.w #12,a7''',1)
s=s.replace(' adda.w #12,a7\n movem.l (a7)+,d0-d7/a0-a1\n rts',' adda.w #12,a7\n rts',1)
p.write_text(s)
