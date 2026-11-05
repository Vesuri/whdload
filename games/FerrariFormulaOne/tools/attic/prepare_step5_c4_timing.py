from pathlib import Path
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-c4-motion-port';repo=r.parents[1]
native=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
sites=[(0x6712e,6,'C4Phase'),(0x67172,8,'C4Countdown'),(0x6734e,10,'C4ClutchStart'),(0x673a4,6,'C4ClutchEnd'),(0x682c0,6,'C4ContactTimer'),(0x6d4f8,6,'C4EventsStart'),(0x6d684,8,'C4EventsEnd'),(0x6d30a,6,'C4AccelGate'),(0x6daba,6,'C4DragGate'),(0x66838,8,'C4FlagTimer')]
s='C4InstallTiming:\n'
for addr,n,label in sites:
 for k in range(0,n,2):s+=f' cmpi.w #${int.from_bytes(native[addr+k:addr+k+2],"big"):04x},${addr+k:x}\n bne.w C1Fault\n'
for addr,n,label in sites:
 s+=f' lea {label}(pc),a0\n move.w #$4ef9,${addr:x}\n move.l a0,${addr+2:x}\n'
 for k in range(6,n,2):s+=f' move.w #$4e71,${addr+k:x}\n'
s+=''' rts
C4Phase:
 addq.b #2,d0
 andi.b #3,d0
 movem.l d0-d1/a0,-(sp)
 move.w $6f272,d1
 bsr.w FF1PhasePulses200
 lea C4PhaseWeight(pc),a0
 move.w d0,(a0)
 movem.l (sp)+,d0-d1/a0
 jmp $67134
C4Countdown:
 subq.w #1,d0
 beq.b .store
 subq.w #1,d0
.store:
 move.w d0,$66f94
 jmp $6717a
C4ContactTimer:
 move.w (a0),d0
 subq.w #1,d0
 beq.b .store
 subq.w #1,d0
.store:
 move.w d0,(a0)
 jmp $682c6
C4ClutchStart:
 move.l a0,-(sp)
 lea C4ClutchLeft(pc),a0
 move.w #2,(a0)
 move.l (sp)+,a0
C4ClutchRun:
 cmpi.l #$10ffff,$66c42
 jmp $67358
C4ClutchEnd:
 move.l a0,-(sp)
 lea C4ClutchLeft(pc),a0
 subq.w #1,(a0)
 move.l (sp)+,a0
 bne.b C4ClutchRun
 move.w $66f92,d0
 jmp $673aa
C4EventsStart:
 move.l a0,-(sp)
 lea C4EventsLeft(pc),a0
 move.w #2,(a0)
 move.l (sp)+,a0
C4EventsRun:
 tst.w $32fbc
 jmp $6d4fe
C4EventsEnd:
 move.l a0,-(sp)
 lea C4EventsLeft(pc),a0
 subq.w #1,(a0)
 move.l (sp)+,a0
 bne.b C4EventsRun
 moveq #0,d0
 move.w d0,$6f13a
 jmp $6d68c
C4AccelGate:
 move.w C4PhaseWeight(pc),d0
 beq.b .skip
 jmp $6d336
.skip:
 jmp $6d44e
C4DragGate:
 move.w C4PhaseWeight(pc),d0
 beq.b .skip
 jmp $6daee
.skip:
 jmp $6dae4
C4FlagTimer:
 subq.w #1,d0
 beq.b .store
 subq.w #1,d0
.store:
 move.w d0,$66be0
 jmp $66840
C4PhaseWeight: dc.w 2
C4ClutchLeft: dc.w 0
C4EventsLeft: dc.w 0
'''
(o/'timing.s').write_text(s)
p=o/'FerrariFormulaOne_Coarse200.s';s=p.read_text();s=s.replace(' bsr.w C4InstallTiming\n','');s=s.replace(' bsr.w install_fuel\n',' bsr.w install_fuel\n bsr.w C4InstallTiming\n');s=s.replace(' include "timing.s"\n','');s=s.replace(' include "motion.s"',' include "timing.s"\n include "motion.s"');p.write_text(s)
# Select the elapsed interval only in this isolated complete timing bring-up.
s=(repo/'Games/FerrariFormulaOne_CoarseInstall.s').read_text().replace(' moveq #100,d0\n bsr.w FF1TimeInit',' move.w #200,d0\n bsr.w FF1TimeInit');(o/'FerrariFormulaOne_CoarseInstall.s').write_text(s)
s=(repo/'Games/FerrariFormulaOne_Coarse.s').read_text().replace('cmpi.l #1,d0','cmpi.l #2,d0').replace('events_pulse: dc.w 1','events_pulse: dc.w 2')
# Repeat the complete recovery tick, including native eligibility, rather than
# incrementing counters past their zero transition or duplicating refill writes.
s=s.replace('recovery_tick:\n','recovery_tick:\n bsr.w C4RecoveryOnce\nC4RecoveryOnce:\n')
(o/'FerrariFormulaOne_Coarse.s').write_text(s)
s=(repo/'Games/FerrariFormulaOne_Presentation.s').read_text()
s=s.replace(' bsr.w FF1InstrumentTick\n',' bsr.w FF1InstrumentTick\n bsr.w B8NativePresentationTick\n bsr.w FF1InstrumentTick\n',1)
s=s.replace(' jsr $6bbfc\n addq.l #4,sp',' jsr $6bbfc\n jsr $6bbfc\n addq.l #4,sp',1)
a=s.index('FF1ClockTick:');b=s.index('FF1ClockDigit:',a)
s=s[:a]+'''FF1ClockTick:
 move.l 4(sp),-(sp)
 lea FF1ClockSimulation(pc),a0
 move.w #1,(a0)
 jsr $22c3a
 ; Re-evaluate the native capped session clock before its second tenth.
 move.l #$226c0,d0
 cmp.l (sp),d0
 bne.b .second
 cmpi.w #12,$1ed2c
 bne.b .second
 tst.w $1c222
 bne.b .second
 cmpi.b #4,$226c4
 bne.b .second
 cmpi.b #5,$226c5
 bne.b .second
 cmpi.b #9,$226c6
 beq.b .done
.second:
 jsr $22c3a
.done:
 move.l a0,-(sp)
 lea FF1ClockSimulation(pc),a0
 clr.w (a0)
 move.l (sp)+,a0
 addq.l #4,sp
 rts

'''+s[b:]
(o/'FerrariFormulaOne_Presentation.s').write_text(s)
# The seven phase-gated proposals carry an explicit 0..2 pulse weight;
# braking and off-road rates continue to use two independently of engine phase.
p=r/'tools/prepare_step5_c4_motion.py';s=p.read_text();needle="(o/'motion.s').write_text(prefix+s)"
replacement='''for site in ('672f0','673fc','67426','67438','6744a','6768e','676e0'):
 a=s.index('velocity_speed_rate_'+site+':');b=s.index('\\n.done:',a)
 segment=s[a:b].replace(' bsr.w velocity_speed_rate',' bsr.w C4WeightedSpeedRate')
 s=s[:a]+segment+s[b:]
s=s.replace(' bsr.w FF1SpeedRate20\\n',' moveq #2,d1\\n bsr.w FF1SpeedRatePulses200\\n')
s+='\\nC4WeightedSpeedRate:\\n lea speed_work(pc),a0\\n move.w C4PhaseWeight(pc),d1\\n bsr.w FF1SpeedRatePulses200\\n tst.l d1\\n bne.w velocity_fault\\n move.w (a0),d0\\n ext.l d0\\n move.w d0,$32fbe\\n rts\\n'
(o/'motion.s').write_text(prefix+s)'''
if 'C4WeightedSpeedRate:' not in s:
 assert needle in s;s=s.replace(needle,replacement);p.write_text(s)
print('Prepared isolated two-pulse timing integration')
