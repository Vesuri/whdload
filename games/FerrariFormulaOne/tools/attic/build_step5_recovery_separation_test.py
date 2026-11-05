from pathlib import Path
import re,struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-recovery-separation-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();asm=(r/'tmp/build/step5-recovery-separation/fine.s').read_text().replace(' bsr.w install_recovery\n',' bsr.w install_recovery\n bsr.w recovery_native_tests\n bra.l recovery_test_stop\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
cases=[]
for mode in (7,8):
 for pulse in (0,1):
  for status in (-25,-2,-1,0,1,2,25):
   for gate in range(6):
    for race in (1,2):
     for presentations in (0,1,3):
      statuses=[status]*8;tyres=[1000]*8;fuel=[12345]*8;flags=[0]*8;fr=[4]*8;wr=[4]*8
      updates=int(mode==7 or pulse)+(presentations if mode==7 else 0)
      for update in range(updates):
       if statuses[0]<-1:statuses[0]+=1
       if gate not in (1,2,3,4):
        for car in range(1,8):
         if gate==5 and car%2:continue
         if statuses[car]>0:
          statuses[car]-=1
          if statuses[car]==0:
           tyres[car]=0xff0000;flags[car]=1
           if mode==8:wr[car]=0
           if race!=2:
            fuel[car]=170000
            if mode==8:fr[car]=0
         elif statuses[car]<-1:statuses[car]+=1
      expected=struct.pack('>8h16I8B16H',*statuses,*tyres,*fuel,*flags,*fr,*wr)
      # Freeze and outer gate prevent the native renderer from visiting its list.
      render_count=0 if presentations and gate not in (1,2) else 0x1234
      cases.append(dict(mode=mode,pulse=pulse,status=status,gate=gate,race=race,presentations=presentations,render_count=render_count,expected_hex=expected.hex()))
extra='''recovery_native_tests:
 ; Temporary test boundaries: execute recovery and projection selection,
 ; return before sorting/drawing or the rest of the player renderer.
 move.w #$4e75,$6c22c
 move.w #$4ef9,$6c7ce
 move.l #$6c91a,$6c7d0
 lea (start.l,pc),a2
 suba.l #5440,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 lea recovery_test_index(pc),a0
 clr.l (a0)
.next:
 move.l recovery_test_index(pc),d0
 cmpi.l #CASECOUNT,d0
 bhs.w .complete
 mulu.w #12,d0
 lea (recovery_test_inputs.l,pc),a5
 adda.l d0,a5
 lea modeval(pc),a0
 move.w (a5),(a0)
 lea events_pulse(pc),a0
 move.w 2(a5),(a0)
 lea recovery_samples(pc),a0
 clr.l (a0)
 clr.w $1c21e
 clr.w $66c7c
 clr.w $66f94
 clr.w $1c222
 move.w 8(a5),$1c1e0
 move.w #17,$1c8ae
 move.w 6(a5),d0
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
 moveq #0,d7
.car:
 move.l d7,d0
 add.w d0,d0
 move.w 4(a5),$2268e(d0.l)
 lea fuel_remainders(pc),a0
 move.w #4,(a0,d0.l)
 lea wear_remainders+8(pc),a0
 move.w #4,(a0,d0.l)
 move.l d7,d0
 lsl.l #2,d0
 move.l #1000,$22356(d0.l)
 move.l #12345,$22376(d0.l)
 clr.b $22604(d7.l)
 clr.b $2260c(d7.l)
 cmpi.w #5,6(a5)
 bne.b .nextcar
 btst #0,d7
 beq.b .nextcar
 move.b #1,$2260c(d7.l)
.nextcar:
 addq.w #1,d7
 cmpi.w #8,d7
 blo.b .car
 move.w #$1234,$6a694
 move.w #1000,$6a60a
 lea $6a60c,a0
 moveq #6,d0
.projections:
 clr.w (a0)+
 dbra d0,.projections
 bsr.w recovery_tick
 ; Simulation must never clear the presentation list, even on a pulse.
 cmpi.w #$1234,$6a694
 beq.b .present
 lea error(pc),a0
 move.l #34,(a0)
.present:
 move.w 10(a5),d7
 beq.b .record
.draw:
 jsr $6c20c
 subq.w #1,d7
 bne.b .draw
.record:
 move.l recovery_test_index(pc),d0
 mulu.w #132,d0
 lea (recovery_test_results.l,pc),a1
 adda.l d0,a1
 bsr.w recovery_snapshot
 move.l error(pc),(a1)+
 move.l recovery_samples(pc),(a1)+
 moveq #0,d0
 move.w $6a694,d0
 move.l d0,(a1)+
 lea recovery_test_index(pc),a0
 addq.l #1,(a0)
 bra.w .next
.complete:
 lea recovery_test_complete(pc),a0
 move.l #1,(a0)
 rts
recovery_test_stop:
 bra.b recovery_test_stop
recovery_test_index: dc.l 0
recovery_test_complete: dc.l 0
'''.replace('CASECOUNT',str(len(cases)))
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'recovery_test_inputs:\n'+''.join(' dc.w '+','.join(str(c[k]) for k in ('mode','pulse','status','gate','race','presentations'))+'\n' for c in cases)+f'recovery_test_results: ds.b {len(cases)*132}\n'
# Isolated calls never execute the motion/event trace paths. Keep their labels
# but avoid allocating hundreds of kilobytes of unused demo records.
unused=('velocity_records','velocity_target_speeds','speed_records','speed_feedback_records','fine_records','heading_records','position_velocity_inputs','steering_records','wear_records','events_records','clocks_records','counters_records','fuel_records','boost_records')
for label in unused:asm=re.sub(r'^'+label+r': ds\.[bl] \d+$',label+': ds.b 4',asm,flags=re.M)
asm=re.sub(r'^recovery_records: ds.b \d+$','recovery_records: ds.b 256',asm,flags=re.M)
asm=re.sub(r'^recovery_contact_records: ds.b \d+$','recovery_contact_records: ds.b 16',asm,flags=re.M)
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-recovery-separation/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'native recovery transition cases')
