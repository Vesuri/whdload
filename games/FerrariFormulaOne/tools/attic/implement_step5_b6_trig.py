from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r.parents[1]/'Games/FerrariFormulaOne_NativeExact.s';s=p.read_text();assert 'FF1TrigReplacement:' not in s
mem=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes();raw=mem[0x24fe0:0x25020]
s=s.replace(' lea FF1NativeSites(pc),a0\n.check:', ''' ifgt FF1_NATIVE_EXACT-3
 lea FF1TrigSignature(pc),a0
 lea $24fe0,a1
 moveq #31,d1
.trig_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.trig_check
 endc
 lea FF1NativeSites(pc),a0
.check:''')
s=s.replace('.complete:\n', '''.complete:
 ifgt FF1_NATIVE_EXACT-3
 lea FF1TrigReplacement(pc),a0
 lea $24fe0,a1
 moveq #15,d1
.trig_copy:
 move.l (a0)+,(a1)+
 dbra d1,.trig_copy
 endc
''')
block=''' ifgt FF1_NATIVE_EXACT-3
; Direct indexed Q15 table lookup. Unlike the initially proposed CCR-dead-only
; version, keep the two original logical shifts: D0 (including upper bits),
; A0 and all five CCR bits exactly match native for every input. Thus existing
; callers and return flags stay valid, including conversion-hook opponents.
; Only the low argument words matter. Masking the angle word is sufficient
; for the signed word index (0..1023); MULS.W replaces the whole D0 afterward.
FF1TrigReplacement:
FF1NativeSine:
 move.w 6(sp),d0
 andi.w #1023,d0
 lea ($2180c,d0.w*2),a0
 move.w 10(sp),d0
 muls.w (a0),d0
 lsr.l #8,d0
 lsr.l #7,d0
 rts
 dcb.b 32-(*-FF1NativeSine),0
FF1NativeCosine:
 move.w 6(sp),d0
 andi.w #1023,d0
 lea ($21a0c,d0.w*2),a0
 move.w 10(sp),d0
 muls.w (a0),d0
 lsr.l #8,d0
 lsr.l #7,d0
 rts
 dcb.b 32-(*-FF1NativeCosine),0
FF1TrigSignature:
'''+ ' dc.w '+','.join('$'+raw[i:i+2].hex() for i in range(0,len(raw),2))+'\n endc\n\n'
s=s.replace('FF1NativeSites:\n',block+'FF1NativeSites:\n');p.write_text(s)
