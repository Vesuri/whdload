from pathlib import Path
import struct,subprocess,json,random,math,os
batch=int(os.environ.get('P1_CASE_BATCH','0'));r=Path(__file__).resolve().parents[1];o=r/f'tmp/build/step5-c4-mul-p2-word-wide-b{batch}';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal)
rng=random.Random(0xc4000);mask=2**32-1
edges=[0,1,2,32767,32768,65535,65536,65537,0x7fffffff,0x80000000,0x80000001,0xfffffffe,mask,0xffff7fff,0xffff8000,0xffff8001]
pairs=[(a,b) for a in edges for b in edges]+[(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(1200)]
# Explicit integer-Q16 products exercise the narrow shortcut across high words.
pairs += [(hi<<16,b) for hi in (0,1,2,32767,32768,32769,65534,65535) for b in edges]
pairs += [(rng.getrandbits(16)<<16,rng.getrandbits(32)) for _ in range(256)]
pairs += [(rng.randrange(-32768,32768)&mask,rng.getrandbits(32)) for _ in range(512)]
signed=lambda n:n if n<2**31 else n-2**32
cases=[]
for a,b in pairs:
 for op in (0,1,3):
  product=(a*b if op==0 else signed(a)*(signed(b) if op==1 else ((b&65535)-65536 if b&32768 else b&65535)))%(2**64)
  cases.append((op,a,b,product&mask,product>>32))
roots=[0,1,2,3,4,2**64-1,2**64-2,2**32-1,2**32,2**63]
for n in edges+[rng.getrandbits(32) for _ in range(1000)]:
 roots.extend(v for v in (n*n-1,n*n,n*n+1) if 0<=v<2**64)
roots.extend(v for k in range(1,33) for v in (2**(2*k)-2,2**(2*k)-1,2**(2*k)) if v<2**64)
roots.extend((1<<52)+d for d in (-2,-1,0,1,2))
roots.extend((1<<k)+d for k in (48,50) for d in (-2,-1,0,1,2))
for i in range(1024,4096):
 for n in (i<<38,((i+1)<<38)-1):
  v=math.isqrt(n);roots.extend(x for x in (n,v*v-1,v*v,v*v+1) if 0<=x<1<<64)
roots.extend(rng.randrange(1<<48,1<<50) for _ in range(4000))
for n in roots:cases.append((2,n&mask,n>>32,math.isqrt(n),n>>32))
total_cases=len(cases);cases=cases[batch*8192:(batch+1)*8192];assert cases
(o/'cases.bin').write_bytes(b''.join(struct.pack('>IIIII',*c) for c in cases))
start=(r/'tmp/build/step5-c3-track-test/track.s').read_text().split('tests:')[0]
s=start+'''tests:
 lea cases(pc),a2
 move.w #COUNT-1,d7
.loop:
 move.l 4(a2),d0
 move.l 8(a2),d1
 move.l #$12345678,d2
 move.l #$abcdef01,d3
 move.l #$76543210,d4
 move.l #$fedcba98,d5
 move.l #$43218765,d6
 move.l sp,a3
 movea.l #$1234abcd,a0
 move.l (a2),-(sp)
 tst.l (sp)+
 beq.b .unsigned
 cmpi.l #1,(a2)
 beq.b .signed
 cmpi.l #3,(a2)
 beq.b .word
 bsr.w FF1SquareRootU64_000
 bra.b .check
.unsigned:
 bsr.w FF1MultiplyU64_000
 bra.b .check
.signed:
 bsr.w FF1MultiplyS64_000
 bra.b .check
.word:
 bsr.w FF1MultiplyS32x16_000
.check:
 cmpa.l #$1234abcd,a0
 bne.b .bad
 cmp.l 12(a2),d0
 bne.b .bad
 cmp.l 16(a2),d1
 bne.b .bad
 cmpi.l #$12345678,d2
 bne.b .bad
 cmpi.l #$abcdef01,d3
 bne.b .bad
 cmpi.l #$76543210,d4
 bne.b .bad
 cmpi.l #$fedcba98,d5
 bne.b .bad
 cmpi.l #$43218765,d6
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
 include "FerrariFormulaOne_Wide000.s"
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 5
outputs: ds.b 12
cases: incbin "cases.bin"
 include "FerrariFormulaOne_Coarse200RootTable.s"
'''.replace('COUNT',str(len(cases)))
(o/'wide.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_C4_ROOT_SEED=1','-DFF1_C4_MUL16=1','-DFF1_C4_MUL16_TEST=1','-Fbin','-quiet','-I'+str(r/'tmp/build/p2-word-source/Games'),'-L','wide.list','-o','wide.bin','wide.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'wide.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'wide.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps(dict(comparisons=len(cases),batch=batch,total_cases=total_cases,scope='Independent Python full-domain boundary/random products and integer square-root; register/stack preservation'))+'\n')
s=(r/'tools/test_step5_c3_trig.py').read_text().replace('step5-c3-trig-test',f'step5-c4-mul-p2-word-wide-b{batch}').replace('c3-trig-oracle',f'c4-mul-p2-word-wide-b{batch}-oracle').replace('trig.list','wide.list').replace('trig.slave','wide.slave').replace('FerrariFormulaOne_Math.s','FerrariFormulaOne_Wide000.s')
s=s.replace("r.parents[1]/'Games'","r/'tmp/build/p2-word-source/Games'")
(r/'tools/test_step5_c4_mul_p2_word_wide.py').write_text(s)
print('Built',len(cases),'wide arithmetic cases')
