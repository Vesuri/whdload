from pathlib import Path
import struct,subprocess,json,random,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-c4-mul-r3c-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal)
(o/'original.bin').write_bytes((r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()[0x29500:0x29542])
source=r.parent.parent/'Games/FerrariFormulaOne_Coarse200MulSites.s';prototype=not source.exists()
if prototype:source=r/'tmp/step5/r3c-sites-draft.s'
rng=random.Random(0xc4c3);mask=0xffffffff
words=[-32768,-32767,-2,-1,0,1,2,127,255,256,32766,32767]
longs=[0,1,2,255,32767,32768,65535,65536,65537,0x7fffffff,0x80000000,0x80000001,0xffff0000,0xffff8000,0xffffffff]
cases=[]
for site in (1,2,3):
 pairs=[(a&mask,b&mask) for a in (words if site==1 else longs) for b in (words if site==3 else longs)]
 for _ in range(1024):pairs.append(((rng.randint(-32768,32767)&mask) if site==1 else rng.getrandbits(32),(rng.randint(-32768,32767)&mask) if site==3 else rng.getrandbits(32)))
 for a,b in pairs:cases.append((site,a,b,rng.choice([0,1,0x80000000,rng.getrandbits(32)]),a if site==1 else 0x01234567))
 for a in longs:
  for b in longs:cases.append((site,a,b,rng.getrandbits(32),a if site==1 else 0x01234567))
 for _ in range(512):cases.append((site,rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32)))
(o/'cases.bin').write_bytes(b''.join(struct.pack('>5I',*v) for v in cases))
start=(r/'tools/build_step5_c4_divide_r3a_oracle.py').read_text();start=start.split("asm='''",1)[1].split('tests:\n',1)[0]
asm=start+'''tests:
 lea cases(pc),a0
 lea outputs(pc),a1
 move.l #COUNT-1,d6
pair_loop:
 move.l (a0),d0
 lea FF1C4MulSite1(pc),a2
 lea reference1(pc),a3
 cmpi.l #1,d0
 beq.b selected
 lea FF1C4MulSite2(pc),a2
 lea reference2(pc),a3
 cmpi.l #2,d0
 beq.b selected
 lea FF1C4MulSite3(pc),a2
 lea reference3(pc),a3
selected:
 suba.w #32,sp
 move.l 12(a0),$10(sp)
 move.l sp,a4
 moveq #0,d7
ccr_loop:
 bsr.w inputs
 move.w d7,ccr
 jsr (a3)
 move.w sr,24(a1)
 movem.l d0-d5,(a1)
 cmpa.l sp,a4
 bne.w failed
 bsr.w inputs
 move.w d7,ccr
 jsr (a2)
 move.w sr,26(a1)
 cmpa.l sp,a4
 bne.w failed
 cmp.l (a1),d0
 bne.w failed
 cmp.l 4(a1),d1
 bne.w failed
 cmp.l 8(a1),d2
 bne.w failed
 cmp.l 12(a1),d3
 bne.w failed
 cmp.l 16(a1),d4
 bne.w failed
 cmp.l 20(a1),d5
 bne.w failed
 move.w 24(a1),d2
 move.w 26(a1),d3
 eor.w d3,d2
 andi.w #$1f,d2
 bne.w failed
 lea checked(pc),a5
 addq.l #1,(a5)
 addq.w #1,d7
 cmpi.w #32,d7
 bne.w ccr_loop
 adda.w #32,sp
 adda.w #20,a0
 dbra d6,pair_loop
 rts
inputs:
 move.l 4(a0),d0
 move.l 8(a0),d1
 move.l 16(a0),d2
 move.l #$89abcdef,d3
 move.l #$76543210,d4
 move.l #$fedcba98,d5
 rts
failed:
 move.l a4,sp
 adda.w #32,sp
 lea error(pc),a5
 addq.l #1,(a5)
 lea failed_case(pc),a5
 move.l a0,(a5)+
 move.l d7,(a5)+
 move.l d0,(a5)+
 move.l d1,(a5)+
 move.l d2,(a5)+
 rts
reference1:
 bsr.w FF1C4MulSiteOriginal
 move.l $14(sp),d1
 rts
reference2:
 bsr.w FF1C4MulSiteOriginal
 moveq #18,d1
 rts
reference3:
 bsr.w FF1C4MulSiteOriginal
 moveq #19,d1
 rts
C1Fault: rts
 include "SOURCE"
FF1C4MulSiteOriginal: incbin "original.bin"
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 5
outputs: ds.b 28
cases: incbin "cases.bin"
'''.replace('COUNT',str(len(cases))).replace('SOURCE',str(source))
(o/'sites.s').write_text(asm)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_C4_MUL_SITES_TEST=1','-Fbin','-quiet','-L','sites.list','-o','sites.bin','sites.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'sites.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'sites.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps(dict(comparisons=len(cases)*32,cases=len(cases),ccr_inputs=32,prototype_only=prototype,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Original native multiply plus overwritten-D1 boundary versus three site paths; D0-D5, SP and all CCR bits; native word domains plus full-domain range misses and independent D2 values for all three sites'),indent=2)+'\n')
s=(r/'tools/test_step5_c4_rotate_r3b_physics.py').read_text().replace('step5-c4-rotate-r3b-physics','step5-c4-mul-r3c-test').replace('c4-rotate-r3b-physics-oracle','c4-mul-r3c-oracle').replace('physics.list','sites.list').replace('physics.slave','sites.slave').replace('FerrariFormulaOne_Physics200.s','FerrariFormulaOne_Coarse200MulSites.s')
s=s.replace("(r.parent.parent/'Games/FerrariFormulaOne_Coarse200MulSites.s')","Path(expected['source'])")
(r/'tools/test_step5_c4_mul_r3c_oracle.py').write_text(s);print('Prepared',len(cases)*32,'native-boundary comparisons; prototype_only=',prototype)
