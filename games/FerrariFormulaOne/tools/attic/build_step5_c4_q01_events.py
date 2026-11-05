from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
# Snapshot every native event destination plus RNG state/pointers and input tables.
blocks=[(0x2268e,32),(0x22356,32),(0x66c3e,64),(0x6ef52,2),(0x6f0f0,4),(0x6f10a,32),(0x6f13a,2),(0x24f60,120),(0x32fbc,2),(0x1c1c4,2),(0x1c5dc,16)]
cases=[]
for car in range(8):
 for status in [-25,-1,0,1]:
  for variant in range(14 if car==0 else 3):
   for seed in [0,65535,137]:cases.append((car,status,variant,seed))
a='''C4QEvents:
 movem.l d0-d7/a0-a6,-(sp)
 lea QOriginal(pc),a1
 bsr.w QSave
 move.l $6d684,-(sp)
 move.l $6d688,-(sp)
 move.l $6d68c,-(sp)
 move.w $6d690,-(sp)
 move.l $24eec,-(sp)
 move.l $24ef0,-(sp)
 move.w $24ef4,-(sp)
 move.w #$4ef9,$24eec
 lea QRng(pc),a0
 move.l a0,$24eee
 lea QCases(pc),a5
 move.w #COUNT-1,d7
.next:
 lea QOriginal(pc),a1
 bsr.w QRestore
 move.w (a5),$32fbc
 lea $2268e,a0
 moveq #7,d0
.status: move.w 2(a5),(a0)+
 dbra d0,.status
 lea $66c3e,a0
 moveq #13,d0
.components: move.l #$3fffff,(a0)+
 dbra d0,.components
 clr.w $6ef52
 move.w #200,$66c76
 move.w #1,$1c1c4
 lea $1c5dc,a0
 moveq #7,d0
.threshold: move.w #32767,(a0)+
 dbra d0,.threshold
 lea $24f60,a0
 moveq #55,d0
.seed: move.w 6(a5),d1
 mulu.w d0,d1
 move.w d1,(a0)+
 dbra d0,.seed
 move.w 4(a5),d0
 tst.w (a5)
 bne.b .opponent
 cmpi.w #13,d0
 beq.b .ready
 cmpi.w #6,d0
 bhs.b .component
 lsl.w #2,d0
 lea QTyres(pc),a0
 move.l (a0,d0.w),a0
 clr.l (a0)
 bra.b .ready
.component:
 subi.w #6,d0
 lsl.w #2,d0
 lea QParts(pc),a0
 move.l (a0,d0.w),a0
 clr.l (a0)
 bra.b .ready
.opponent:
 lea $22356,a0
 moveq #7,d1
.tyre: move.l #70000,(a0)+
 dbra d1,.tyre
 move.w (a5),d1
 lsl.w #2,d1
 lea $22356,a0
 subq.w #1,d0
 ext.l d0
 add.l d0,(a0,d1.w)
.ready:
 lea QRngCount(pc),a0
 clr.l (a0)
 lea QInitial(pc),a1
 bsr.w QSave
 ; Independent oracle: execute original native event body once per pulse,
 ; re-entering its original eligibility guards each time.
 move.w #$4ef9,$6d684
 lea QNativeReturn(pc),a0
 move.l a0,$6d686
 bsr.w QNativePulse
 bsr.w QNativePulse
 lea QExpected(pc),a1
 bsr.w QSave
 lea QExpectedRng(pc),a0
 move.l QRngCount(pc),(a0)
 lea QInitial(pc),a1
 bsr.w QRestore
 lea QRngCount(pc),a0
 clr.l (a0)
 ; Restore installed C4 end hook and call its installed start hook.
 move.l 20(sp),$6d684
 move.l 16(sp),$6d688
 move.w #$4ef9,$6d68c
 lea QReturn(pc),a0
 move.l a0,$6d68e
 bsr.w QCandidatePulse
 lea QActual(pc),a1
 bsr.w QSave
 lea QExpected(pc),a0
 lea QActual(pc),a1
 move.w #WORDS-1,d0
.compare:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w QBad
 dbra d0,.compare
 move.l QRngCount(pc),d0
 cmp.l QExpectedRng(pc),d0
 bne.w QBad
 move.w #COUNT-1,d1
 sub.w d7,d1
 lsl.w #2,d1
 lea QRngResults(pc),a0
 move.l d0,(a0,d1.w)
 lea QChecked(pc),a0
 addq.l #1,(a0)
 addq.l #8,a5
 dbra d7,.next
 move.w (sp)+,$24ef4
 move.l (sp)+,$24ef0
 move.l (sp)+,$24eec
 move.w (sp)+,$6d690
 move.l (sp)+,$6d68c
 move.l (sp)+,$6d688
 move.l (sp)+,$6d684
 lea QOriginal(pc),a1
 bsr.w QRestore
 movem.l (sp)+,d0-d7/a0-a6
 rts
QNativePulse:
 movem.l d0-d7/a0-a6,-(sp)
 move.l #123,-(sp)
 bsr.w QNativeBody
 addq.l #4,sp
 movem.l (sp)+,d0-d7/a0-a6
 rts
QNativeBody:
 link a6,#-8
 tst.w $32fbc
 jmp $6d4fe
QCandidatePulse:
 movem.l d0-d7/a0-a6,-(sp)
 move.l #123,-(sp)
 bsr.w QCandidateBody
 addq.l #4,sp
 movem.l (sp)+,d0-d7/a0-a6
 rts
QCandidateBody:
 link a6,#-8
 jmp $6d4f8
QNativeReturn:
 moveq #0,d0
 move.w d0,$6f13a
QReturn:
 unlk a6
 rts
QRng:
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea QRngCount(pc),a0
 addq.l #1,(a0)
 move.l (sp)+,a0
 move.w (sp)+,ccr
 link a6,#-2
 move.l $24fd4,a0
 jmp $24ef6
QBad:
 lea error(pc),a0
 move.l #4101,(a0)
 bra.w C1Fault
'''
# Offsets from saved stack: last word=0, longs=2,6, word=10, longs=12,16.
a=a.replace('20(sp),$6d684','20(sp),$6d684')
for mode in ['Save','Restore']:
 a+='Q'+mode+':\n movem.l d0/a0-a1,-(sp)\n'
 for i,(address,n) in enumerate(blocks):
  a+=f' lea ${address:x},a0\n move.w #{n//2-1},d0\n.copy{i}:\n'+(' move.w (a0)+,(a1)+\n' if mode=='Save' else ' move.w (a1)+,(a0)+\n')+f' dbra d0,.copy{i}\n'
 a+=' movem.l (sp)+,d0/a0-a1\n rts\n'
n=sum(n for _,n in blocks)
a+='QChecked: dc.l 0\nQRngCount: dc.l 0\nQExpectedRng: dc.l 0\n'
a+='QTyres: dc.l $66c52,$66c56,$66c5a,$66c5e,$66c6a,$66c6e\nQParts: dc.l $66c62,$66c66,$66c4a,$66c4e,$66c72,$66c3e,$66c42\n'
for label in ['Original','Initial','Expected','Actual']:a+=f'Q{label}: ds.b {n}\n'
a+='QRngResults: ds.l '+str(len(cases))+'\nQCases:\n'+''.join(' dc.w '+','.join(str(x) for x in c)+'\n' for c in cases)
a=a.replace('COUNT',str(len(cases))).replace('WORDS',str(n//2))
(r/'tools/step5_c4_q01_events.s').write_text(a)
(r/'manifest/step5-c4-q01-event-cases.json').write_text(json.dumps({'cases':cases,'blocks':blocks},indent=2)+'\n')
s=(r/'tools/build_step5_c4_divide_frame_r3g_ab.py').read_text().replace('step5-c4-divide-frame-r3g-v1-ab','step5-c4-q01-events')
inject="import shutil\nshutil.copy(r/'tools/step5_c4_q01_events.s',o/'qevents.s')\np=o/'FerrariFormulaOne_CoarseInstall.s'\np.write_text((r.parents[1]/'Games/FerrariFormulaOne_CoarseInstall.s').read_text().replace(' bsr.w FF1TimeInit',' bsr.w FF1TimeInit\\n bsr.w C4QEvents'))\n"
# Bind every fixture pointer explicitly; dc.l data is intentionally not inferred.
s=s.replace('s=s.replace(repr(\'data_candidates=[]\\n\')', "extra+=\"for label,values in [('QTyres',[0x66c52,0x66c56,0x66c5a,0x66c5e,0x66c6a,0x66c6e]),('QParts',[0x66c62,0x66c66,0x66c4a,0x66c4e,0x66c72,0x66c3e,0x66c42])]:\\n for index,value in enumerate(values):addlong(symbols[label]+4*index,value,'Q01 directed component pointer')\\n\"\ns=s.replace(repr(\'data_candidates=[]\\n\')",1)
s=s.replace('exec(compile(s,',"s=s.replace('base=(r/',"+repr(inject)+"+'base=(r/',1)\ns=s.replace('public_bindings:', ' include \"qevents.s\"\\npublic_bindings:')\nexec(compile(s,",1)
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
