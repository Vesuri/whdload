from pathlib import Path
import struct,subprocess,json,hashlib,itertools
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v5-velocity-carry-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
cases=[]
def add(v,rem,c,s):
 x,z=[a*5+b for a,b in zip(v,rem)]
 tails=[(x*c-z*s)//32768,(x*s+z*c)//32768]
 q=[(abs(a)//5)*(1 if a>=0 else -1) for a in tails];rr=[a-b*5 for a,b in zip(tails,q)]
 overflow=any(not -2**31<=a<2**31 for a in q)
 if overflow:q=v[:];rr=rem[:]
 cases.append(dict(vector=v,remainders=rem,cos=c,sin=s,expected=[q[0]&0xffffffff,q[1]&0xffffffff,((rr[0]&65535)<<16)|(rr[1]&65535),0xffffffff if overflow else 0]))
mem=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
for angle in range(1024):
 s,c=[struct.unpack_from('>h',mem,b+angle*2)[0] for b in (0x2180c,0x21a0c)]
 for v,rem in (([1234567,-7654321],[4,-4]),([-1,1],[-4,4]),([2**31-1,-2**31],[3,-3])):add(v,rem,c,s)
for c,s in itertools.product((-32768,-32767,-1,0,1,32767),repeat=2):
 for v in ([2**31-1,2**31-1],[-2**31,-2**31],[0,0],[1,-1]):add(v,[4,-4],c,s)
asm=prefix+''' lea (vectors,pc),a3
 lea results(pc),a4
 move.w #COUNT-1,d7
.loop:
 lea state(pc),a0
 lea remainders(pc),a1
 move.l (a3),(a0)
 move.l 4(a3),4(a0)
 move.l 8(a3),(a1)
 move.w 12(a3),d0
 move.w 14(a3),d1
 bsr.w FF1VelocityRotateCarry020
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 move.l (a1),(a4)+
 move.l d1,(a4)+
 adda.w #16,a3
 dbra d7,.loop
 rts
'''.replace('COUNT',str(len(cases)))
for name in ('Math','Step','Velocity'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+name+'.s'))+'"\n'
asm+='installed: dc.l 0\nstate: ds.l 2\nremainders: ds.w 2\nresults: ds.l '+str(len(cases)*4)+'\nvectors: incbin "vectors.bin"\n'
(o/'vectors.bin').write_bytes(b''.join(struct.pack('>iihhhh',*c['vector'],*c['remainders'],c['cos'],c['sin']) for c in cases))
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'velocity carry rotation cases')
