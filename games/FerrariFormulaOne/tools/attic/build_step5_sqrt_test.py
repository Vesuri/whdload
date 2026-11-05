from pathlib import Path
import struct,subprocess,json,random,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-sqrt-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
normal=base[32:-4];size=len(normal)
(o/'original.bin').write_bytes((r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()[0x25770:0x257ac])
values={0,1,0x7fffffff,0x80000000,0xffffffff}
for root in range(1024):
 for delta in (-1,0,1):
  if root*root+delta>=0:values.add(root*root+delta)
rng=random.Random(0xF1);values.update(rng.getrandbits(32) for _ in range(512));values=sorted(values)
(o/'values.bin').write_bytes(b''.join(struct.pack('>I',a) for a in values))
(o/'expected.json').write_text(json.dumps({'inputs':len(values),'ccr_values':32,'comparisons':len(values)*32,'checks':['D0-D3 outputs including upper words','CCR XNZVC','every bounded perfect square and neighbors','random full-width inputs']},indent=2)+'\n')
asm='''start:
 add.l $1c(a3),d0
 move.l d0,a1
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 cmp.l #$64a68,d0
 bne.w done
 lea installed(pc),a0
 tst.l (a0)
 bne.w done
 addq.l #1,(a0)
 lea barrier(pc),a0
 move.l a0,$654e8
 bsr.w tests
done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
barrier: jmp $2a130
tests:
 lea values(pc),a0
 lea outputs(pc),a1
 move.l #COUNT-1,d6
value_loop:
 moveq #0,d7
ccr_loop:
 move.l #$01234567,d2
 move.l #$89abcdef,d3
 move.l (a0),-(sp)
 move.w d7,ccr
 bsr.w original
 addq.l #4,sp
 move.w sr,32(a1)
 movem.l d0-d3,(a1)
 move.l #$01234567,d2
 move.l #$89abcdef,d3
 move.l (a0),-(sp)
 move.w d7,ccr
 bsr.w FF1SquareRoot020
 addq.l #4,sp
 move.w sr,34(a1)
 movem.l d0-d3,16(a1)
 cmp.l (a1),d0
 bne.b failed
 cmp.l 4(a1),d1
 bne.b failed
 cmp.l 8(a1),d2
 bne.b failed
 cmp.l 12(a1),d3
 bne.b failed
 move.w 32(a1),d2
 move.w 34(a1),d3
 eor.w d3,d2
 andi.w #$1f,d2
 bne.b failed
 lea checked(pc),a3
 addq.l #1,(a3)
 addq.w #1,d7
 cmpi.w #32,d7
 bne.w ccr_loop
 addq.l #4,a0
 dbra d6,value_loop
 rts
failed:
 lea error(pc),a3
 addq.l #1,(a3)
 lea failed_case(pc),a3
 move.l (a0),(a3)+
 move.l d7,(a3)+
 rts
 include "CORE"
original: incbin "original.bin"
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 2
outputs: ds.b 36
values: incbin "values.bin"
'''.replace('COUNT',str(len(values))).replace('CORE',str(r.parent.parent/'Games/FerrariFormulaOne_Sqrt.s'))
(o/'test.s').write_text(asm)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','test.list','-o','test.bin','test.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'test.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'test.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built',len(values)*32,'square-root comparisons')
