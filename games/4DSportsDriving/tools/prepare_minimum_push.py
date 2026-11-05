from pathlib import Path
import shutil
base=Path('tmp/fixtures/matched-takeoff-minpush');assert not base.exists();shutil.copytree('tmp/fixtures/matched-takeoff222/source',base/'source')
src=base/'source'
p=src/'4DSportsDrivingHD.s';s=p.read_text();needle='    PL_PSS $CB48,sim_a4000_wheel,142';assert needle in s;s=s.replace(needle,'    PL_PS $D110,sim_minimum_push\n'+needle);p.write_text(s)
p=src/'simulation_a4000.s';s=p.read_text();s+='''
; Disposable bounded contact experiment. Preserve the native query/ray and
; stale residual; only shorten positive inclined push magnitudes <=512.
; Exhaustive search avoids assuming monotonicity. Native modes and unusual
; correction paths retain their original vector. No persistent private state.
sim_minimum_push:
 move.l d0,-(sp)
 moveq #0,d0
 addx.w d0,d0
 move.w d0,-(sp)
 cmp.w #50,-$15fa(a4)
 bne .original
 cmp.w #4,$96(a4)
 blt .original
 tst.b -$1ca(a5)
 bne .original
 tst.w -$3e(a5)
 ble .original
 cmp.w #512,-$3e(a5)
 bhi .original
 movem.l d0-d7/a0-a6,-(sp)
 lea -12(sp),sp
 move.l sp,a2
 move.w -$3e(a5),d7
 moveq #1,d6
.trial:
 move.w d6,-$3e(a5)
 movem.l d2-d7/a2-a6,-(sp)
 move.l a2,d0
 move.w $96(a4),d1
 muls #34,d1
 add.l $224(a4),d1
 add.l #16,d1
 move.l d1,a1
 lea -$40(a5),a0
 jsr -$7bd8(a4)
 movem.l (sp)+,d2-d7/a2-a6
 movem.l d2-d7/a2-a6,-(sp)
 subq.l #8,sp
 move.w $96(a4),(sp)
 move.l -$e6(a5),a3
 move.l a2,a0
 lea 2(sp),a1
 moveq #2,d2
.coord:
 move.w (a0)+,d1
 ext.l d1
 move.l (a3)+,d0
 add.l d1,d0
 asr.l #6,d0
 move.w d0,(a1)+
 dbra d2,.coord
 lea sim_minimum_push(pc),a6
 adda.l #sim_game-sim_minimum_push,a6
 move.l (a6),a6
 adda.l #$1185e,a6
 jsr (a6)
 addq.l #8,sp
 movem.l (sp)+,d2-d7/a2-a6
 tst.w d0
 bpl .found
 addq.w #1,d6
 cmp.w d7,d6
 bls .trial
 move.w d7,-$3e(a5)
.found:
 lea 12(sp),sp
 movem.l (sp)+,d0-d7/a0-a6
.original:
 move.w (sp)+,d0
 lsr.w #1,d0
 move.l (sp)+,d0
 lea -$46(a5),a0
 move.l a0,d0
 rts
''';p.write_text(s)
print(base)
