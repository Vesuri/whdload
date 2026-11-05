from pathlib import Path
import json,struct,re,subprocess
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-s3-flags';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
s=(r/'tmp/build/step5-s3/lean-p0/fine.s').read_text().replace(' bsr.w FF1InstallPresentation\n',' bsr.w FF1InstallPresentation\n bsr.w flag_tests\n bra.l flag_test_stop\n')
cases=[]
for race in (1,2):
 for session in (0,1):
  for counter in (0,1,5):
   for arg in range(6):
    for passes in (0,1,3):
     graphic=arg if race==2 and arg else 5
     if session:graphic=3
     after=counter-1 if session and counter else counter
     cases.append(dict(race=race,session=session,counter=counter,arg=arg,passes=passes,expected_hex=struct.pack('>HHII',after,graphic,passes*2,0).hex()))
extra='''
flag_tests:
 lea flag_blit(pc),a0
 move.l a0,$66888
 move.l a0,$668d8
 lea start(pc),a2
 suba.l #5440,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 lea flag_test_index(pc),a0
 clr.l (a0)
.next:
 move.l flag_test_index(pc),d0
 cmpi.l #COUNT,d0
 bhs.w .done
 mulu.w #10,d0
 lea (flag_test_inputs.l,pc),a5
 adda.l d0,a5
 move.w (a5),$1c1e0
 move.w 2(a5),$1c222
 move.w 4(a5),$66be0
 lea flag_blit_calls(pc),a0
 clr.l (a0)
 move.w 6(a5),d0
 ext.l d0
 move.l d0,-(sp)
 jsr $66802
 addq.l #4,sp
 move.w 8(a5),d7
 beq.b .record
.draw:
 movem.l d7/a5,-(sp)
 bsr.w FF1PresentFlag
 movem.l (sp)+,d7/a5
 subq.w #1,d7
 bne.b .draw
.record:
 move.l flag_test_index(pc),d0
 mulu.w #12,d0
 lea (flag_test_results.l,pc),a1
 adda.l d0,a1
 move.w $66be0,(a1)+
 move.w FF1FlagGraphic(pc),(a1)+
 move.l flag_blit_calls(pc),(a1)+
 move.l error(pc),(a1)+
 lea flag_test_index(pc),a0
 addq.l #1,(a0)
 bra.w .next
.done:
 lea flag_test_complete(pc),a0
 move.l #1,(a0)
 rts
flag_blit:
 move.w ccr,-(sp)
 move.l a0,-(sp)
 lea flag_blit_calls(pc),a0
 addq.l #1,(a0)
 move.l (sp)+,a0
 move.w (sp)+,ccr
 jmp $24ae0
flag_blit_calls: dc.l 0
flag_test_stop: bra.b flag_test_stop
flag_test_index: dc.l 0
flag_test_complete: dc.l 0
flag_test_inputs:
'''.replace('COUNT',str(len(cases)))
extra+=''.join(' dc.w '+','.join(str(c[k]) for k in ('race','session','counter','arg','passes'))+'\n' for c in cases)
extra+=f'flag_test_results: ds.b {len(cases)*12}\n'
s=s.replace(' FF1UpdateWorkspace',extra+' FF1UpdateWorkspace')
(o/'fine.s').write_text(s);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-s3/lean-p0/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-I'+str(r.parents[1]/'Games'),'-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);listing=(o/'fine.list').read_text();entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16);assert size+entry<32768;struct.pack_into('>H',code,24,size+entry)
pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);struct.pack_into('>I',h,20,len(code)//4);h[28:32]=h[20:24];(o/'fine.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
print(len(cases),'status flag state/drawing cases')
