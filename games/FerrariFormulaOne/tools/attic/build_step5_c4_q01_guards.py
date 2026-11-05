from pathlib import Path
import json
r=Path(__file__).resolve().parents[1]
values=[-32768,-2,-1,0,1,2,3,32767]
cases=[]
for kind in range(3):
 for car in (range(8) if kind==1 else [0]):
  for value in values:
   for flag in ([0,1] if kind==2 else [1]):
    expected=value
    for pulse in range(2):
     if (kind==1 and expected>0) or (kind!=1 and expected!=0 and flag):expected=((expected-1+32768)%65536)-32768
    cases.append([kind,car,value,flag,expected])
blocks=[(0x6717c,6),(0x6719e,6),(0x682c6,6),(0x683c2,6),(0x66840,6),(0x66f94,2),(0x66be0,2),(0x1c222,2),(0x32f30,16)]
a='C4QGuards:\n movem.l d0-d7/a0-a6,-(sp)\n lea QGuardSaved(pc),a1\n'
for i,(addr,n) in enumerate(blocks):a+=f' lea ${addr:x},a0\n moveq #{n//2-1},d0\n.save{i}: move.w (a0)+,(a1)+\n dbra d0,.save{i}\n'
for addr,n in blocks[:5]:a+=f' move.w #$4ef9,${addr:x}\n lea QGuardReturn(pc),a0\n move.l a0,${addr+2:x}\n'
a+=''' lea QGuardCases(pc),a5
 move.w #COUNT-1,d7
.next:
 move.w 4(a5),$66f94
 move.w 4(a5),$66be0
 move.w 6(a5),$1c222
 lea $32f30,a0
 moveq #7,d0
.seed: move.w 4(a5),(a0)+
 dbra d0,.seed
 move.l #123,-(sp)
 bsr.w QGuardRun
 addq.l #4,sp
 tst.w (a5)
 beq.b .countdown
 cmpi.w #1,(a5)
 beq.b .contact
 move.w $66be0,d0
 bra.b .compare
.countdown: move.w $66f94,d0
 bra.b .compare
.contact:
 move.w 2(a5),d0
 add.w d0,d0
 lea $32f30,a0
 move.w (a0,d0.w),d0
.compare:
 cmp.w 8(a5),d0
 bne.w QGuardBad
 lea QGuardChecked(pc),a0
 addq.l #1,(a0)
 adda.w #10,a5
 dbra d7,.next
 lea QGuardSaved(pc),a1
'''
for i,(addr,n) in enumerate(blocks):a+=f' lea ${addr:x},a0\n moveq #{n//2-1},d0\n.restore{i}: move.w (a1)+,(a0)+\n dbra d0,.restore{i}\n'
a+=''' movem.l (sp)+,d0-d7/a0-a6
 rts
QGuardRun:
 link a6,#-24
 tst.w (a5)
 beq.b .countdown
 cmpi.w #1,(a5)
 beq.b .contact
 jmp $6681c
.countdown: jmp $67164
.contact:
 move.w 2(a5),16(sp)
 move.w 2(a5),d0
 add.w d0,d0
 lea $32f30,a0
 adda.w d0,a0
 jmp $682a8
QGuardReturn:
 unlk a6
 rts
QGuardBad:
 lea error(pc),a0
 move.l #4102,(a0)
 bra.w C1Fault
QGuardChecked: dc.l 0
'''
a+=f'QGuardSaved: ds.b {sum(n for _,n in blocks)}\nQGuardCases:\n'
a+=''.join(' dc.w '+','.join(map(str,c))+'\n' for c in cases)
a=a.replace('COUNT',str(len(cases)))
(r/'tools/step5_c4_q01_guards.s').write_text(a)
(r/'manifest/step5-c4-q01-guard-cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(r/'tools/build_step5_c4_q01_events.py').read_text()
s=s.replace("(r/'tools/step5_c4_q01_events.s').write_text(a)","a+='\\n'+(r/'tools/step5_c4_q01_guards.s').read_text()\n(r/'tools/step5_c4_q01_events.s').write_text(a)")
s=s.replace("a=a.replace('COUNT'", "a=a.replace(' movem.l (sp)+,d0-d7/a0-a6\\n rts\\nQNativePulse:', ' bsr.w C4QGuards\\n movem.l (sp)+,d0-d7/a0-a6\\n rts\\nQNativePulse:')\na=a.replace('COUNT'")
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
