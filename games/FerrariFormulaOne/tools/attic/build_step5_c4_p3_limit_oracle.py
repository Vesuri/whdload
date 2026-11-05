from pathlib import Path
import struct,subprocess,json,random,os
r=Path(__file__).resolve().parents[1];mode=int(os.environ.get('P3_MODE','0'));o=r/f'tmp/build/step5-c4-p3-limit-oracle-{mode}';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal);mask=2**32-1;rng=random.Random(0xc403)
aw=[0,1,-1,32767,32768,-32768,-32769,0x7fffffff,0x80000000,0xffffffff,0x12348000,0xffff7fff,65535,65536]
bw=[-32768,-1,0,1,2,32767,32768,0xffff0001];ds=[0,1,2,3,32767,32768,65535,65536,0xffffffff]
inputs=[(a&mask,b&mask,d) for a in aw for b in bw for d in ds]
inputs += [(rng.getrandbits(32),rng.getrandbits(32),rng.randrange(1,65536) if i%2 else rng.getrandbits(32)) for i in range(5000)]
s16=lambda x:(x&65535)-65536 if x&32768 else x&65535
cases=[]
for a,b,d in inputs:
 out=a;status=mask
 if s16(b)>=0 and 1<=d<=65535:
  n=s16(a)*s16(b);q=abs(n)//d;q=-q if n<0 else q
  if -32768<=q<=32767:out=q&mask;status=0
 cases.append((a,b,d,out,status))
(o/'cases.bin').write_bytes(b''.join(struct.pack('>IIIII',*x) for x in cases))
start=(r/'tmp/build/step5-c3-track-test/track.s').read_text().split('tests:')[0]
helper=(r.parents[1]/'Games/FerrariFormulaOne_Coarse200Adapters.s').read_text();helper=helper[helper.index('FF1VelocityLimit020:'):helper.index('FF1SquareRootU32:')]
s=start+'''tests:
 lea FF1DivLimitControl(pc),a0
 move.w #MODE,(a0)
 lea cases(pc),a2
 move.w #COUNT-1,d7
.loop:
 move.l (a2),d0
 move.l 4(a2),d1
 move.l 8(a2),d2
 move.l #$12345678,d3
 move.l #$87654321,d4
 move.l #$abcdef01,d5
 move.l #$76543210,d6
 movea.l #$1234abcd,a0
 movea.l #$5678abcd,a1
 move.l sp,a3
 bsr.w FF1VelocityLimit020
 cmp.l 12(a2),d0
 bne.b .bad
 cmp.l 16(a2),d1
 bne.b .bad
 cmp.l 8(a2),d2
 bne.b .bad
 cmpi.l #$12345678,d3
 bne.b .bad
 cmpi.l #$87654321,d4
 bne.b .bad
 cmpi.l #$abcdef01,d5
 bne.b .bad
 cmpi.l #$76543210,d6
 bne.b .bad
 cmpa.l #$1234abcd,a0
 bne.b .bad
 cmpa.l #$5678abcd,a1
 bne.b .bad
 cmpa.l sp,a3
 bne.b .bad
 lea checked(pc),a1
 addq.l #1,(a1)
 adda.w #20,a2
 dbra d7,.loop
 rts
.bad:
 lea error(pc),a1
 move.l #1,(a1)
 lea failed_case(pc),a1
 move.l a2,(a1)+
 move.l d0,(a1)+
 move.l d1,(a1)+
 move.l d7,(a1)+
 move.l sp,(a1)+
 rts
'''.replace('MODE',str(mode)).replace('COUNT',str(len(cases)))+helper+'''
 include "FerrariFormulaOne_Math.s"
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 5
cases: incbin "cases.bin"
'''
(o/'wide.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_C4_DIV_LIMIT=1','-DFF1_MATH_000_ONLY=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','wide.list','-o','wide.bin','wide.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'wide.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'wide.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps({'comparisons':len(cases),'mode':mode,'scope':'Independent signed-word product, truncating quotient, invalid input/range rollback; full register and stack preservation'})+'\n')
s=(r/'tools/test_step5_c4_wide.py').read_text().replace('step5-c4-wide',f'step5-c4-p3-limit-oracle-{mode}').replace('c4-wide-oracle',f'c4-p3-limit-oracle-{mode}').replace('FerrariFormulaOne_Wide000.s','FerrariFormulaOne_Coarse200Adapters.s');(r/'tools/test_step5_c4_p3_limit_oracle.py').write_text(s)
print('Built',len(cases),'velocity-limit cases, mode',mode)
