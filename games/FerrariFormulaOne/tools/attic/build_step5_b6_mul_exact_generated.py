from pathlib import Path
import struct,subprocess,json,random,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b6-mul-exact-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
normal=base[32:-4];size=len(normal)
(o/'original.bin').write_bytes((r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()[0x29500:0x29542])
edges={0,1,2,3,0x7fffffff,0x80000000,0x80000001,0xffffffff}
for bit in (8,15,16,17,24,30):
 for delta in (-1,0,1):
  v=(1<<bit)+delta;edges.update((v,(-v)&0xffffffff))
pairs=[(a,b) for a in sorted(edges) for b in sorted(edges)];rng=random.Random(0xF1)
pairs += [(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(512)]
pairs += [(rng.getrandbits(32),rng.randint(1,65535)) for _ in range(512)]
(o/'pairs.bin').write_bytes(b''.join(struct.pack('>II',a,b) for a,b in pairs))
(o/'expected.json').write_text(json.dumps({'pairs':len(pairs),'ccr_values':32,'comparisons':len(pairs)*32,'checks':['quotient','remainder','CCR XNZVC','D2-D5 preservation']},indent=2)+'\n')
asm='''start:
 add.l $1c(a3),d0
 move.l d0,a1
 movem.l d0-a6,-(sp)
 move.w ccr,-(sp)
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
 lea FF1Divide000(pc),a2
 move.w modeval(pc),d0
 tst.w d0
 beq.b selected
 lea FF1NativeMultiply(pc),a2
selected:
 lea pairs(pc),a0
 lea outputs(pc),a1
 move.l #PAIRCOUNT-1,d6
pair_loop:
 moveq #0,d7
ccr_loop:
 move.l #$01234567,d2
 move.l #$89abcdef,d3
 move.l #$76543210,d4
 move.l #$fedcba98,d5
 move.l (a0),d0
 move.l 4(a0),d1
 move.w d7,ccr
 bsr.w original
 move.w ccr,8(a1)
 move.l d0,(a1)
 move.l d1,4(a1)
 move.l (a0),d0
 move.l 4(a0),d1
 move.w d7,ccr
 jsr (a2)
 move.w ccr,10(a1)
 cmp.l (a1),d0
 bne.w failed
 cmp.l 4(a1),d1
 bne.w failed
 cmpi.l #$01234567,d2
 bne.w failed
 cmpi.l #$89abcdef,d3
 bne.w failed
 cmpi.l #$76543210,d4
 bne.w failed
 cmpi.l #$fedcba98,d5
 bne.w failed
 move.w 8(a1),d2
 move.w 10(a1),d3
 eor.w d3,d2
 andi.w #$1f,d2
 bne.w failed
 lea checked(pc),a3
 addq.l #1,(a3)
 addq.w #1,d7
 cmpi.w #32,d7
 bne.w ccr_loop
 addq.l #8,a0
 dbra d6,pair_loop
 rts
failed:
 lea error(pc),a3
 addq.l #1,(a3)
 lea failed_case(pc),a3
 move.l (a0),(a3)+
 move.l 4(a0),(a3)+
 move.l d7,(a3)+
 move.l d0,(a3)+
 move.l d1,(a3)+
 rts
 include "CORE"
original: incbin "original.bin"
modeval: dc.w MODE
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 5
outputs: ds.b 12
pairs: incbin "pairs.bin"
'''.replace('PAIRCOUNT',str(len(pairs))).replace('CORE',str(r.parent.parent/'Games/FerrariFormulaOne_Math.s'))
asm+='\nFF1NativeMultiply:'+(r.parent.parent/'Games/FerrariFormulaOne_NativeExact.s').read_text().split('FF1NativeMultiply:')[1].split('FF1MultiplySignature:')[0]
for mode in (1,):
 name='div'+str(mode);(o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built',len(pairs)*32,'division comparisons per CPU implementation')
