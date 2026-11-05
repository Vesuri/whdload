from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v5-seed-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
import math,random
cases=[]
roots={0,1,2,3,31,255,1023,65535,65536,2**31-1,2**31,2**32-1}
roots|={max(0,2**k+d) for k in range(32) for d in (-1,0,1)}
values={0,2**64-1}
for root in roots:
 for offset in (-1,0,1):
  if 0<=root*root+offset<2**64:values.add(root*root+offset)
rng=random.Random(481)
values.update(rng.randrange(2**64) for _ in range(128))
values.update(n for k in range(256,1024) for n in (k<<54,((k+1)<<54)-1))
for n in sorted(values):cases.append(dict(input=n,expected=[math.isqrt(n),n>>32,0x13579bdf,0]))
asm=prefix+' lea inputs(pc),a4\n lea results(pc),a3\n move.w #'+str(len(cases)-1)+',d7\n.loop:\n move.l (a4)+,d1\n move.l (a4)+,d0\n move.l #$13579bdf,d2\n bsr.w FF1SquareRootU64\n move.l d0,(a3)+\n move.l d1,(a3)+\n move.l d2,(a3)+\n clr.l (a3)+\n dbra d7,.loop\n rts\n'
asm+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Sqrt.s')+'"\ninstalled: dc.l 0\ninputs:\n'
for c in cases:asm+=' dc.l $'+format(c['input']>>32,'08x')+',$'+format(c['input']&0xffffffff,'08x')+'\n'
asm+='results: ds.l '+str(len(cases)*4)+'\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'unsigned 64-bit square root cases')
