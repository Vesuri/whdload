from pathlib import Path
import struct,subprocess,json,hashlib,itertools
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v5-velocity-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
cases=[];sentinel=[0x12345678,-0x76543210]
def add(op,old,new=(0,0),c=0,s=0,alias=0):
 if op==0:out=[5*(b-a) for a,b in zip(old,new)]
 elif op==3:out=[(old[0]*s)//32768,(old[0]*c)//32768]
 elif op==1:out=[(old[0]*c-old[1]*s)//32768,(old[0]*s+old[1]*c)//32768]
 else:out=[x<<16 for x in new]
 overflow=any(not -2**31<=x<2**31 for x in out)
 initial=old if op==1 or alias==1 else new if alias==2 else sentinel
 expected=(initial if overflow else out)+[-1 if overflow else 0]
 cases.append(dict(op=op,old=old,new=new,cos=c,sin=s,alias=alias,expected=[x&0xffffffff for x in expected]))
for old,new in itertools.product((-2**31,-429496730,-429496729,-65537,-1,0,1,65537,429496729,429496730,2**31-1),repeat=2):
 for alias in (0,1,2):add(0,[old,-1],[new,1],alias=alias);add(0,[-1,old],[1,new],alias=alias)
mem=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
for angle in range(1024):
 s=struct.unpack_from('>h',mem,0x2180c+angle*2)[0];c=struct.unpack_from('>h',mem,0x21a0c+angle*2)[0]
 for vector in ([1234567,-45678901],[-65537,32769],[2147483647,-2147483648]):add(1,vector,c=c,s=s)
 for speed in (-2**31,-1234567,0,1234567,2**31-1):add(3,[speed,0],c=c,s=s)
for c,s in itertools.product((-32768,-32767,-1,0,1,32767),repeat=2):
 for vector in ([2**31-1,2**31-1],[-2**31,-2**31],[0,0],[1,-1]):add(1,vector,c=c,s=s)
for c,s in ((-32768,0),(0,-32768),(-32768,-32768)):
 add(3,[-2**31,0],c=c,s=s)
for x,z in itertools.product((-32768,-1,0,1,32767),repeat=2):add(2,sentinel,new=[x,z])
asm=prefix+''' lea vectors(pc),a3
 lea results(pc),a4
 move.l #COUNT-1,d7
.loop:
 lea state(pc),a2
 move.l #$12345678,(a2)
 move.l #$89abcdf0,4(a2)
 lea scratch(pc),a5
 move.l 8(a3),(a5)
 move.l 12(a3),4(a5)
 move.l 16(a3),8(a5)
 move.l 20(a3),12(a5)
 move.l a5,a0
 lea 8(a5),a1
 move.w (a3),d6
 beq.b .derivative
 cmpi.w #1,d6
 beq.b .rotation
 cmpi.w #3,d6
 beq.b .project
 move.l a2,a0
 move.l 16(a3),d0
 move.l 20(a3),d1
 bsr.w FF1VelocityReset
 moveq #0,d1
 bra.b .save
.project:
 move.l a2,a0
 move.l 8(a3),d0
 move.w 4(a3),d1
 move.w 2(a3),d2
 bsr.w FF1VelocityProject020
 bra.b .save
.rotation:
 move.l (a0),(a2)
 move.l 4(a0),4(a2)
 move.l a2,a0
 move.w 2(a3),d0
 move.w 4(a3),d1
 bsr.w FF1VelocityRotate020
 bra.b .save
.derivative:
 cmpi.w #1,6(a3)
 bne.b .not_old
 move.l a0,a2
.not_old:
 cmpi.w #2,6(a3)
 bne.b .ready
 move.l a1,a2
.ready:
 bsr.w FF1VelocityDerivative20
.save:
 move.l (a2),(a4)+
 move.l 4(a2),(a4)+
 move.l d1,(a4)+
 adda.w #24,a3
 dbra d7,.loop
 rts
'''.replace('COUNT',str(len(cases)))
asm+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Math.s')+'"\n'
asm+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Step.s')+'"\n'
asm+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Velocity.s')+'"\n'
asm+='installed: dc.l 0\nstate: ds.l 2\nscratch: ds.l 4\n'
# Keep both data bases within PC-relative reach; long case offsets are indexed.
asm+='results: ds.l '+str(len(cases)*3)+'\nvectors: incbin "vectors.bin"\n'
# The large output array precedes vectors; use a 68020 full PC displacement.
asm=asm.replace('lea vectors(pc),a3','lea (vectors,pc),a3')
(o/'vectors.bin').write_bytes(b''.join(struct.pack('>HhhHiiii',x['op'],x['cos'],x['sin'],x['alias'],*x['old'],*x['new']) for x in cases))
(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'fine.s').write_text(asm)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'velocity cases')
coarse=[x for x in cases if x['op'] in (0,2)]
coarseasm=asm.replace('move.l #'+str(len(cases))+'-1,d7','move.l #'+str(len(coarse))+'-1,d7').replace('results: ds.l '+str(len(cases)*3),'results: ds.l '+str(len(coarse)*3)).replace('vectors.bin','coarse-vectors.bin')
(o/'coarse-vectors.bin').write_bytes(b''.join(struct.pack('>HhhHiiii',x['op'],x['cos'],x['sin'],x['alias'],*x['old'],*x['new']) for x in coarse))
(o/'coarse.json').write_text(json.dumps(coarse,indent=2)+'\n');(o/'coarse.s').write_text(coarseasm)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L','coarse.list','-o','coarse.bin','coarse.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'coarse.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'coarse.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(coarse),'68000-safe velocity cases (not coarse interval acceptance)')
