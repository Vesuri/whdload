from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-position-ownership-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
s=(r/'tools/build_step5_position_test.py').read_text();prefix=s[s.index("prefix='''")+10:s.index("'''\ncases=[]")]
initial=b''.join(struct.pack('>hHh',i*11-80,1+i*4001,i%9-4) for i in range(16))
cases=[];vectors=[]
for dst in range(16):
 expected=bytearray(initial);expected[dst*6+2:dst*6+6]=bytes(4)
 cases.append({'action':'reset_same_integer','destination_axis':dst,'expected':list(struct.unpack('>24I',expected))})
 vectors.append(struct.pack('>4h',0,dst*6,0,dst*11-80))
for axis in range(2):
 for dest in range(8):
  for src in range(8):
   dst=dest*2+axis;source=src*2+axis;new=500-dest*97+src
   expected=bytearray(initial);expected[dst*6:dst*6+2]=struct.pack('>h',new);expected[dst*6+2:dst*6+6]=initial[source*6+2:source*6+6]
   cases.append({'action':'assign','destination_axis':dst,'source_axis':source,'expected':list(struct.unpack('>24I',expected))})
   vectors.append(struct.pack('>4h',1,dst*6,source*6,new))
asm=prefix+''' lea vectors(pc),a3
 lea results(pc),a4
 move.w #COUNT-1,d7
next_case:
 lea initial(pc),a0
 lea state(pc),a1
 moveq #23,d6
copy_initial:
 move.l (a0)+,(a1)+
 dbra d6,copy_initial
 move.w (a3)+,d5
 move.w (a3)+,d0
 lea state(pc),a0
 adda.w d0,a0
 move.w (a3)+,d0
 lea state(pc),a1
 adda.w d0,a1
 move.w (a3)+,d0
 tst.w d5
 bne.b assign_case
 bsr.w FF1PositionReset
 bra.b save_case
assign_case:
 bsr.w FF1PositionAssign
save_case:
 lea state(pc),a0
 moveq #23,d6
copy_result:
 move.l (a0)+,(a4)+
 dbra d6,copy_result
 dbra d7,next_case
 rts
'''.replace('COUNT',str(len(cases)))
for module in ('Math','Step','Position'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
asm+='installed: dc.l 0\nstate: ds.b 96\ninitial: incbin "initial.bin"\nvectors: incbin "vectors.bin"\nresults: ds.b '+str(len(cases)*96)+'\n'
(o/'initial.bin').write_bytes(initial);(o/'vectors.bin').write_bytes(b''.join(vectors));name='fine'
(o/(name+'.s')).write_text(asm);(o/(name+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'position ownership cases')
