from pathlib import Path
root=Path('src');out=Path('tmp/p4-before');out.mkdir(exist_ok=True)
for name in ['HardDrivinTime.s','HardDrivinPhase.s','HardDrivinProjection.s']:
 p=root/name;(out/name).write_bytes(p.read_bytes())
p=root/'HardDrivinTime.s';s=p.read_text();s=s.replace('_time_scale_word:\n\tcmpi.w #8,d1','''_time_scale_word:
	; Native engine endpoints use n=8 with zero carry. This exact identity
	; avoids both multiplication and division on the common scalar path.
	cmpi.w #8,d1
	bne.s .scaled
	tst.l d2
	bne.s .scaled
	ext.l d0
	rts
.scaled:
	cmpi.w #8,d1''',1)
s=s.replace('_time_normalize_angle:\n\tmovem.l', '''_time_normalize_angle:
	; One wrap is sufficient for [-2160,2160], including signed +/-720
	; endpoints. Keep the full-long reducer for large elapsed-time angles.
	cmpi.l #720,d0
	bgt.s .positive_bounded
	cmpi.l #-720,d0
	bge.s .bounded_done
	cmpi.l #-2160,d0
	blt.s .general
	addi.l #1440,d0
	rts
.positive_bounded:
	cmpi.l #2160,d0
	bgt.s .general
	subi.l #1440,d0
.bounded_done:
	rts
.general:
	movem.l''',1);p.write_text(s)
p=root/'HardDrivinPhase.s';s=p.read_text();a=s.index(' move.w 2(a0),-(a7)',s.index('_phase_prepare_anchor:'));b=s.index(' move.w d0,-$66da(a4)',a)
s=s[:a]+''' ; Exactly the two native $2950 MULS.W/DIVS.W conversions. Each call
 ; consumes signed words; preserve that narrowing even if DIVS overflows.
 ; Normal anchors are RPM0..6500, ratio7..10 /450..800, then500/140.
 move.w -$66d6(a4),d0
 muls.w (a0),d0
 divs.w 2(a0),d0
 muls.w #500,d0
 divs.w #140,d0
'''+s[b:]
s=s.replace(' move.l (a0)+,d0\n asr.l #3,d0\n move.l d0,d3\n move.w PH_DT(a6),d1',''' move.l (a0)+,d0
 move.w PH_DT(a6),d1
 cmpi.w #8,d1
 bne.s .fractional
 ; Eight adds of ASR(vector,3) equal vector with its bottom three bits
 ; cleared, including negative and held-skid vectors with fine fractions.
 andi.l #$fffffff8,d0
 bra.s .accumulate
.fractional:
 asr.l #3,d0
 move.l d0,d3''',1).replace(' dbf d1,.times\n add.l (a1),d0',' dbf d1,.times\n.accumulate:\n add.l (a1),d0',1)
s=s.replace('_phase_scalar_step:\n moveq #0,d3','''_phase_scalar_step:
 ; At a complete new phase current=anchor, so consuming all eight fields
 ; returns the native endpoint exactly. Retain the general kernel when the
 ; caller supplies a different current value (including verification inputs).
 cmpi.w #8,d1
 bne.s .incremental
 move.l (a0),d3
 cmp.l 4(a0),d3
 bne.s .incremental
 swap d0
 clr.w d0
 move.l d0,4(a0)
 rts
.incremental:
 moveq #0,d3''',1)
s=s.replace(' bsr _projection_integer_components\n move.w d0,(a1)',''' bsr _projection_integer_components
 tst.w d7
 beq.s .integer
 move.w d0,(a1)''',1)
s=s.replace(' dbf d6,.axis\n adda.w #12,a7',''' dbf d6,.axis
 bra.s .done
.integer:
 ; Zero Q6 fraction needs only one native projection. Preserve signed word
 ; narrowing and Q16 storage, including cardinal and negative components.
 move.w d0,(a0)
 clr.w 2(a0)
 move.w d1,4(a0)
 clr.w 6(a0)
 move.w d2,8(a0)
 clr.w 10(a0)
.done:
 adda.w #12,a7''',1)
p.write_text(s)
