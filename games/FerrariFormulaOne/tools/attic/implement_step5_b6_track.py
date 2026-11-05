from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r.parents[1]/'Games/FerrariFormulaOne_NativeExact.s';s=p.read_text();assert 'FF1NativeLookahead:' not in s
mem=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes();track=mem[0x6977a:0x6988c];caller=mem[0x67514:0x6752a]
s=s.replace(' lea FF1NativeSites(pc),a0\n.check:',f''' ifgt FF1_NATIVE_EXACT-2
 lea FF1TrackSignature(pc),a0
 lea $6977a,a1
 move.w #{len(track)//2-1},d1
.track_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.track_check
 lea $67514,a1
 moveq #{len(caller)//2-1},d1
.caller_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.caller_check
 endc
 lea FF1NativeSites(pc),a0
.check:''')
s=s.replace(' beq.b .done\n move.l d0,a1',' beq.w .complete\n move.l d0,a1')
s=s.replace('.bad:\n lea error', '''.complete:
 ifgt FF1_NATIVE_EXACT-2
 lea FF1NativeLookahead(pc),a0
 move.w #$4ef9,$6977a
 move.l a0,$6977c
 move.w #$4e71,$69780
 endc
 bra.b .done
.bad:
 lea error''')
s=s.replace('FF1NativeSites:\n', ''' ifgt FF1_NATIVE_EXACT-2
; Only native caller $67514: drops argument, consumes D0, overwrites A0 and
; XNZVC by $67528, overwrites D1 at $6755e on both intervening branch paths.
; The native argument-slot mutation and D1/A0 scratch outputs are dead there.
FF1NativeLookahead:
 tst.w $1ed8a
 bne.b .native
 moveq #0,d1
 move.w $2268c,d1
 cmpi.w #12,d1
 blo.b .native
 ; At count 32767 the last segment +2 wraps the native signed word.
 ; Keep native behavior for that whole boundary domain.
 cmpi.w #32766,d1
 bhi.b .native
 move.w 6(sp),d0
 ext.l d0
 bmi.b .native
 cmp.l d1,d0
 bhs.b .native
 lea $1dc24,a0
 bra.w FF1TrackLookaheadNormal
.native:
 link a6,#-8
 clr.l -6(a6)
 jmp $69782
 include "FerrariFormulaOne_Track.s"
FF1TrackSignature:
'''+''.join(' dc.w '+','.join('$'+b[i:i+2].hex() for i in range(0,len(b),2))+'\n' for b in [track,caller])+''' endc

FF1NativeSites:
''')
p.write_text(s)
