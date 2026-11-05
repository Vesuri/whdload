from pathlib import Path
import struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-counter-transition';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
asm=(r/'tmp/build/step5-counters-fine/fine.s').read_text().replace(' bsr.w install_counters\n',' bsr.w install_counters\n bsr.w counter_native_tests\n bra.l counter_test_stop\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
extra='counter_native_tests:\n'
for a in (0x6713a,0x6719e,0x673aa):
 extra+=f' cmpi.w #${m[a:a+2].hex()},${a:x}\n bne.w velocity_fault\n move.w #$4e75,${a:x}\n'
# Flush instruction caches after planting the isolated return boundaries.
extra+=' lea (start.l,pc),a2\n suba.l #5440,a2\n move.l $1180(a2),a2\n jsr $20(a2)\n'
cases=[]
def setup(mode,pulse):
 return f' lea modeval(pc),a0\n move.w #{mode},(a0)\n lea events_pulse(pc),a0\n move.w #{pulse},(a0)\n lea counters_samples(pc),a0\n clr.l (a0)\n'
def emit(kind,mode,pulse,before,expected,settings):
 global extra
 i=len(cases);cases.append(dict(kind=kind,mode=mode,pulse=pulse,before=before,settings=settings,expected=expected))
 extra+=setup(mode,pulse)
 for addr,size,value in settings:extra+=f' move.{size} #${value&((1<<({"b":8,"w":16,"l":32}[size]))-1):x},${addr:x}\n'
 addr,entry={'phase':(0x1be42,0x67128),'countdown':(0x66f94,0x67164),'clutch':(0x32f2e,0x6734e)}[kind]
 extra+=f' move.{"b" if kind=="phase" else "w"} #{before},${addr:x}\n jsr ${entry:x}\n lea (counter_test_results+{i*16}.l,pc),a3\n moveq #0,d0\n move.{"b" if kind=="phase" else "w"} ${addr:x},d0\n move.l d0,(a3)+\n moveq #0,d0\n move.w $32f92,d0\n move.l d0,(a3)+\n move.l counters_samples(pc),(a3)+\n move.l error(pc),(a3)+\n'
for mode in (7,8):
 for pulse in (0,1):
  run=int(mode==7 or pulse)
  for before in range(4):emit('phase',mode,pulse,before,[(before+run)%4,0,1,0],[(0x32f92,'w',0)])
  for before in (0,1,2,10,32767):
   for same_segment in (False,True):
    for input_state in (1,2):
     for old_latch in (0,1):
      after=before-run if before else 0
      latch=1 if before==1 and run and not same_segment and input_state==2 else old_latch
      emit('countdown',mode,pulse,before,[after,latch,int(before!=0),0],[(0x32f92,'w',old_latch),(0x1c1e6,'w',7),(0x6a60a,'w',7 if same_segment else 8),(0x66f92,'w',input_state)])
  for before in (0,1,9,10):
   for reason in ('eligible','condition','fuel','input','speed'):
    eligible=reason=='eligible';after=(before+1 if eligible and before<10 else max(before-1,0)) if run else before
    settings=[(0x32f92,'w',0),(0x66c42,'l',0x10ffff if reason=='condition' else 0x200000),(0x22376,'l',0 if reason=='fuel' else 1),(0x66f92,'w',2 if reason=='input' else 3),(0x32fbe,'w',1 if reason=='speed' else 0)]
    emit('clutch',mode,pulse,before,[after,0,1,0],settings)
extra+=' lea counter_test_complete(pc),a0\n move.l #1,(a0)\n rts\ncounter_test_stop:\n bra.b counter_test_stop\ncounter_test_complete: dc.l 0\n'
asm=body+extra+'velocity_records: ds.b 64000'+buffers+f'counter_test_results: ds.b {len(cases)*16}\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-counters-fine/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'native counter transition cases')
