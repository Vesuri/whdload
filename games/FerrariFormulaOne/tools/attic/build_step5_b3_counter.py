from pathlib import Path
import re,struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b3-v4-contact-counter';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
asm=(r/'tmp/build/step5-b3-v4/verify/fine.s').read_text().replace(' bsr.w install_recovery\n',' bsr.w install_recovery\n bsr.w contact_native_tests\n bra.l contact_test_stop\n',1)
asm=asm.replace(' include \"FerrariFormulaOne_UpdateHooks.s\"',(r.parents[1]/'Games/FerrariFormulaOne_UpdateHooks.s').read_text())
body,buffers=asm.split('\n FF1UpdateWorkspace\n',1)
extra='contact_native_tests:\n'
for a in (0x682c6,):extra+=f' cmpi.w #${m[a:a+2].hex()},${a:x}\n bne.w velocity_fault\n move.w #$4e75,${a:x}\n'
extra+=' lea (start.l,pc),a2\n suba.l #5440,a2\n move.l $1180(a2),a2\n jsr $20(a2)\n'
cases=[]
for mode in (7,8):
 for pulse in (0,1):
  for car in range(8):
   for before in (1,2,25,32767):
    after=before-int(mode==7 or pulse or car!=0);i=len(cases);cases.append(dict(mode=mode,pulse=pulse,car=car,before=before,expected=[after,after,int(car==0),0]));addr=0x32f30+2*car
    extra+=f' lea modeval(pc),a0\n move.w #{mode},(a0)\n lea events_pulse(pc),a0\n move.w #{pulse},(a0)\n lea recovery_contacts(pc),a0\n clr.l (a0)\n move.w #{car},$32fbc\n move.w #{before},${addr:x}\n lea ${addr:x},a0\n moveq #0,d0\n jsr $682c0\n lea (contact_test_results+{i*16}.l,pc),a3\n moveq #0,d1\n move.w ${addr:x},d1\n move.l d1,(a3)+\n move.l d0,(a3)+\n move.l recovery_contacts(pc),(a3)+\n move.l error(pc),(a3)+\n'
extra+=' lea contact_test_complete(pc),a0\n move.l #1,(a0)\n rts\ncontact_test_stop:\n bra.b contact_test_stop\ncontact_test_complete: dc.l 0\ncontact_test_local: ds.l 2\n'
asm=body+'\n'+extra+'\n FF1UpdateWorkspace\n'+buffers+f'contact_test_results: ds.b {len(cases)*16}\n'
# Isolated calls never execute the motion/event trace paths. Keep their labels
# but avoid allocating hundreds of kilobytes of unused demo records.
unused=('velocity_records','velocity_target_speeds','speed_records','speed_feedback_records','fine_records','heading_records','position_velocity_inputs','steering_records','wear_records','events_records','clocks_records','counters_records','fuel_records','boost_records')
for label in unused:asm=re.sub(r'^'+label+r': ds\.[bl] \d+$',label+': ds.b 4',asm,flags=re.M)
asm=re.sub(r'^recovery_records: ds.b \d+$','recovery_records: ds.b 256',asm,flags=re.M)
asm=re.sub(r'^recovery_contact_records: ds.b \d+$','recovery_contact_records: ds.b 16',asm,flags=re.M)
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-b3-v4/verify/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-DVERIFY=1','-DFF1_PLAN_B=1','-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-I'+str(r.parents[1]/'Games'),'-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',(o/'fine.list').read_text(),re.M)[1],16);assert len(code)+entry<32768;struct.pack_into('>H',code,24,len(code)+entry);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'native contact-counter cases')
