from pathlib import Path
import struct,json
r=Path(__file__).resolve().parents[1]
cases=[]
for status in (-25,-2,-1,0,1,2,25):
 for gate in range(6):
  for race in (1,2):
   statuses=[status]*8;tyres=[1000]*8;fuel=[12345]*8;flags=[0]*8;wr=[4]*8;fr=[4]*8
   for pulse in range(2):
    if statuses[0]<-1:statuses[0]+=1
    if gate not in (1,2,3,4):
     for car in range(1,8):
      if gate==5 and car%2:continue
      if statuses[car]>0:
       statuses[car]-=1
       if statuses[car]==0:
        tyres[car]=0xff0000;flags[car]=1;wr[car]=0
        if race!=2:fuel[car]=170000;fr[car]=0
      elif statuses[car]<-1:statuses[car]+=1
   expect=struct.pack('>8h16I8B16H',*statuses,*tyres,*fuel,*flags,*fr,*wr)
   cases.append(dict(status=status,gate=gate,race=race,expected_hex=expect.hex()))
blocks=[('$2268e',16),('$22356',32),('$22376',32),('$22604',8),('$2260c',8),('$1c21e',2),('$66c7c',2),('$66f94',2),('$1c222',2),('$1c1e0',2),('$1c8ae',2),('$6a694',2),('$6a60a',16),('fuel_remainders',16),('wear_remainders+8',16)]
def lea(addr,reg):return ' lea '+addr+('' if addr.startswith('$') else '(pc)')+','+reg+'\n'
asm='C4TestRecovery:\n movem.l d0-d7/a0-a6,-(sp)\n lea C4RecoverySaved(pc),a1\n'
for i,(addr,n) in enumerate(blocks):asm+=lea(addr,'a0')+f' moveq #{n//2-1},d0\n.save{i}:\n move.w (a0)+,(a1)+\n dbra d0,.save{i}\n'
asm+=''' lea public_bindings(pc),a5
 dc.w $dbfc
 dc.l C4RecoveryCases-public_bindings
 moveq #83,d7
.next:
 clr.w $1c21e
 clr.w $66c7c
 clr.w $66f94
 clr.w $1c222
 move.w 4(a5),$1c1e0
 move.w #17,$1c8ae
 move.w 2(a5),d0
 cmpi.w #1,d0
 bne.b .gate2
 move.w #1,$1c21e
.gate2:
 cmpi.w #2,d0
 bne.b .gate3
 move.w #1,$66c7c
.gate3:
 cmpi.w #3,d0
 bne.b .gate4
 move.w #1,$66f94
.gate4:
 cmpi.w #4,d0
 bne.b .states
 move.w #1,$1c222
.states:
 moveq #0,d6
.car:
 move.w d6,d0
 add.w d0,d0
 lea $2268e,a0
 move.w (a5),(a0,d0.w)
 lea fuel_remainders(pc),a0
 move.w #4,(a0,d0.w)
 lea wear_remainders+8(pc),a0
 move.w #4,(a0,d0.w)
 add.w d0,d0
 lea $22356,a0
 move.l #1000,(a0,d0.w)
 lea $22376,a0
 move.l #12345,(a0,d0.w)
 lea $22604,a0
 clr.b (a0,d6.w)
 lea $2260c,a0
 clr.b (a0,d6.w)
 cmpi.w #5,2(a5)
 bne.b .nextcar
 btst #0,d6
 beq.b .nextcar
 move.b #1,(a0,d6.w)
.nextcar:
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .car
 move.w #$1234,$6a694
 move.w #1000,$6a60a
 lea $6a60c,a0
 moveq #6,d0
.projections:
 clr.w (a0)+
 dbra d0,.projections
 movem.l d0-d7/a0-a6,-(sp)
 bsr.w recovery_tick
 movem.l (sp)+,d0-d7/a0-a6
 cmpi.w #$1234,$6a694
 bne.w C4RecoveryBad
 lea 6(a5),a1
'''
for i,(addr,n) in enumerate([('$2268e',16),('$22356',32),('$22376',32),('$22604',8),('fuel_remainders',16),('wear_remainders+8',16)]):asm+=lea(addr,'a0')+f' moveq #{n//2-1},d0\n.check{i}:\n move.w (a0)+,d1\n cmp.w (a1)+,d1\n bne.w C4RecoveryBad\n dbra d0,.check{i}\n'
asm+=''' lea C4RecoveryChecked(pc),a0
 addq.l #1,(a0)
 adda.w #126,a5
 dbra d7,.next
 lea C4RecoverySaved(pc),a1
'''
for i,(addr,n) in enumerate(blocks):asm+=lea(addr,'a0')+f' moveq #{n//2-1},d0\n.restore{i}:\n move.w (a1)+,(a0)+\n dbra d0,.restore{i}\n'
asm+=''' movem.l (sp)+,d0-d7/a0-a6
 rts
C4RecoveryBad:
 lea error(pc),a0
 move.l #4001,(a0)
 bra.w C1Fault
C4RecoveryChecked: dc.l 0
C4RecoverySaved: ds.b '''+str(sum(n for _,n in blocks))+'\n'
data='C4RecoveryCases:\n'
for c in cases:
 data+=' dc.w '+','.join(str(c[k]) for k in ('status','gate','race'))+'\n'
 words=struct.unpack('>60H',bytes.fromhex(c['expected_hex']));data+=' dc.w '+','.join('$%04x'%v for v in words)+'\n'
(r/'tools/step5_c4_final_recovery_fixture.s').write_text(asm)
(r/'tools/step5_c4_final_recovery_data.s').write_text(data)
(r/'manifest/step5-c4-final-recovery-cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(r/'tools/build_step5_c4_final_timer_test.py').read_text().replace('final-timer','final-recovery').replace('final_timer','final_recovery').replace('timer-tests','recovery-tests').replace('C4TestTimers','C4TestRecovery')
s=s.replace('import shutil\\n','import shutil\\nshutil.copy(r/\'tools/step5_c4_final_recovery_data.s\',o/\'recovery-data.s\')\\n')
# Append the large immutable case table after existing public tables, keeping code displacements unchanged.
s=s.replace(' include \\"FerrariFormulaOne_Coarse200BoundaryTable.s\\"\\\\n', ' include \\"FerrariFormulaOne_Coarse200BoundaryTable.s\\"\\\\n include \\"recovery-data.s\\"\\\\n')
assert 'include \\"recovery-data.s' in s
exec(compile(s,str(r/'tools/build_step5_c1.py'),'exec'))
