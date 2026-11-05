from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v5-speed-feedback-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
import math,random
cases=[]
def add(x,z,rx,rz):
 ax,az=5*x+rx,5*z+rz
 bad=not(-4<=rx<=4 and -4<=rz<=4 and -2**31<=5*x<2**31 and -2**31<=5*z<2**31 and -2**31<=ax<2**31 and -2**31<=az<2**31)
 q,rem=0x12345678,3
 if not bad:
  norm=math.isqrt(ax*ax+az*az)
  if norm<4*65536*5:q,rem=0,0
  elif norm>=500*65536*5:q,rem=500*65536,0
  else:q,rem=divmod(norm,5)
 cases.append(dict(vector=[x,z],remainders=[rx,rz],expected=[q,rem,0xffffffff if bad else 0,0]))
for speed in (0,1,4,5,100,499,500,501,6553):
 for offset in (-1,0,1):
  for rx in (-4,0,4):
   for rz in (-4,0,4):
    add(speed*65536+offset,0,rx,rz);add(0,-speed*65536+offset,rx,rz)
for x,z,rx,rz in ((3*65536,4*65536,0,0),(-2**31,0,0,0),(2**31-1,0,0,0),(0,0,5,0),(0,0,0,-5)):
 add(x,z,rx,rz)
rng=random.Random(481)
for _ in range(512):add(rng.randrange(-500*65536,500*65536),rng.randrange(-500*65536,500*65536),rng.randrange(-4,5),rng.randrange(-4,5))
asm=prefix
asm+=' lea inputs(pc),a4\n lea results(pc),a3\n move.w #'+str(len(cases)-1)+',d7\n.loop:\n lea state(pc),a0\n move.l (a4)+,(a0)\n move.l (a4)+,4(a0)\n move.l (a4)+,8(a0)\n lea output(pc),a1\n move.l #$12345678,(a1)\n move.w #3,4(a1)\n bsr.w FF1SpeedFromVelocity020\n move.l (a1),(a3)+\n moveq #0,d0\n move.w 4(a1),d0\n move.l d0,(a3)+\n move.l d1,(a3)+\n clr.l (a3)+\n dbra d7,.loop\n rts\n'
for module in ('Speed','Sqrt'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
asm+='installed: dc.l 0\nstate: ds.b 12\noutput: ds.b 6\ninputs:\n'
for c in cases:asm+=' dc.l '+','.join(str(v) for v in c['vector'])+'\n dc.w '+','.join(str(v) for v in c['remainders'])+'\n'
asm+='results: ds.l '+str(len(cases)*4)+'\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'scalar feedback cases')
