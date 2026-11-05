from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-heading-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
s=(r/'tools/build_step5_position_test.py').read_text();prefix=s[s.index("prefix='''")+10:s.index("'''\ncases=[]")]
for variant in ('coarse','fine'):
 cases=[];vectors=[]
 def emit(op,state,increment,expected,status=0):
  raw=struct.pack('>IhIh',state[0]&0xffffffff,state[1],state[2]&0xffffffff,state[3])
  output=struct.pack('>IhIhI',expected[0]&0xffffffff,expected[1],expected[2]&0xffffffff,expected[3],status&0xffffffff)
  cases.append(dict(operation=op,input=state,increment=increment,expected=list(struct.unpack('>4I',output))))
  vectors.append(struct.pack('>H',op)+raw+struct.pack('>IH',increment&0xffffffff,0))
 if variant=='fine':
  for angle,rem in ((0,0),(0x7fffffff,4),(-0x80000000,-4)):
   for increment in ([1]*5+[-1]*5+[34567,-12345,0,0x7fffffff,-0x80000000]):
    total=increment+rem;bad=not -0x80000000<=total<=0x7fffffff
    q=0 if bad else (abs(total)//5)*(1 if total>=0 else -1)
    nr=rem if bad else total-q*5;na=angle if bad else (angle+q)&0xffffffff
    emit(0,[angle,rem,1234,2],increment,[na,nr,1234,2],-1 if bad else 0);angle,rem=na,nr
 for a,w in ((0,0),(123456,-654321),(0x7fffffff,-0x80000000)):
  for ra in range(-4,5):
   for rw in range(-4,5):
    diff=rw-ra;q=(abs(diff)//5)*(1 if diff>=0 else -1)
    emit(1,[a,ra,w,rw],0,[0,0,(w-a+q)&0xffffffff,diff-q*5])
 for angle in (0,-123456,0x7fffffff,-0x80000000):
  for rem in (-4,0,4):
   emit(2,[angle,rem,1234,2],angle,[angle,0,1234,2])
   emit(3,[angle,rem,1234,2],angle,[angle,2,1234,2])
 asm=prefix+''' lea vectors(pc),a3
 lea results(pc),a4
 move.w #COUNT-1,d7
heading_loop:
 move.w (a3)+,d6
 lea state(pc),a0
 move.l (a3)+,(a0)
 move.l (a3)+,4(a0)
 move.l (a3)+,8(a0)
 move.l (a3)+,d0
 addq.l #2,a3
 moveq #0,d1
 tst.w d6
 bne.b .not_step
 bsr.w FF1Heading20
 bra.b .save
.not_step:
 cmpi.w #1,d6
 bne.b .not_zero
 bsr.w FF1HeadingZeroRelative
 bra.b .save
.not_zero:
 cmpi.w #2,d6
 bne.b .assign
 bsr.w FF1HeadingReset
 bra.b .save
.assign:
 lea 6(a0),a1
 bsr.w FF1HeadingAssign
.save:
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 move.l 8(a0),(a4)+
 move.l d1,(a4)+
 dbra d7,heading_loop
 rts
'''.replace('COUNT',str(len(cases)))
 for module in ('Math','Step','Heading'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
 asm+='installed: dc.l 0\nstate: ds.b 12\nvectors: incbin "'+variant+'-vectors.bin"\nresults: ds.l '+str(len(cases)*4)+'\n'
 (o/(variant+'-vectors.bin')).write_bytes(b''.join(vectors));name=variant;(o/(name+'.s')).write_text(asm);(o/(name+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
 print(variant,len(cases),'angular carry/wrap/ownership cases')
