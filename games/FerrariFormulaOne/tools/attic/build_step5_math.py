from pathlib import Path
import struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-math-v3';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
b=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes();(o/'original_div.bin').write_bytes(b[0x293d0:0x29412])
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
 cmpi.l #$48e73c00,$293d0
 bne.w bad
 cmpi.l #$4eb90002,$654e6
 bne.w bad
 cmpi.w #$a130,$654ea
 bne.w bad
 addq.l #1,(a0)
 lea barrier(pc),a0
 move.l a0,$654e8
 bra.w done
bad:
 lea error(pc),a0
 move.l #1,(a0)
done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
barrier:
 jsr $2a130
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 lea ticks(pc),a0
 addq.l #1,(a0)
 cmpi.l #126,(a0)
 bne.w finish
 move.w modeval(pc),d0
 tst.w d0
 beq.b omit
 move.w #$4ef9,$293d0
 lea fastdiv(pc),a1
 cmpi.w #2,d0
 bne.b plant
 lea verifydiv(pc),a1
plant:
 move.l a1,$293d2
omit:
 move.w #$4ef9,$65714
 lea logic_tail(pc),a1
 move.l a1,$65716
 move.w #$4ef9,$65f2e
 move.l #$65174,$65f30
 cmpi.w #3,d0
 bne.b finish
 lea start(pc),a2
 suba.l #NORMALSIZE,a2
 move.l $1180(a2),a2
 lea cache_api(pc),a0
 move.l a2,(a0)
 move.l #$13e,d0
 move.l #$13f,d1
 jsr $60(a2)
 lea cache_old(pc),a0
 move.l d0,(a0)
 lea cache_called(pc),a0
 addq.l #1,(a0)
finish:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
logic_tail:
 movem.l d0-d7/a0-a6,-(sp)
 move.w $66faa,d0
 ext.l d0
 move.l d0,-(sp)
 jsr $6bbfc
 addq.l #4,sp
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65d6e
; Unsigned magnitude division preserves native INT_MIN / -1 wrapping.
; All native sign restoration and zero cases retain the original instructions.
fastdiv:
 movem.l d2-d5,-(sp)
 move.l d1,d5
 beq.b zerodiv
 bpl.b divisor_positive
 neg.l d1
divisor_positive:
 move.l d0,d4
 beq.b zeronum
 bpl.b numerator_positive
 neg.l d0
numerator_positive:
 divul.l d1,d2:d0
 andi #$ef,ccr
 move.l d2,d1
 eor.l d4,d5
 bpl.b quotient_positive
 neg.l d0
quotient_positive:
 eor.l d1,d4
 bpl.b divdone
 neg.l d1
 bra.b divdone
zeronum:
 clr.l d1
zerodiv:
 clr.l d0
divdone:
 movem.l (sp)+,d2-d5
 rts
verifydiv:
 movem.l d2-d7/a0-a1,-(sp)
 move.w sr,-(sp)
 move.l d0,d6
 move.l d1,d7
 move.w (sp),ccr
 bsr.w originaldiv
 move.w sr,-(sp)
 movem.l d0-d1,-(sp)
 move.l d6,d0
 move.l d7,d1
 move.w 10(sp),ccr
 bsr.w fastdiv
 move.w sr,-(sp)
 cmp.l 2(sp),d0
 bne.b verifybad
 cmp.l 6(sp),d1
 bne.b verifybad
 move.w (sp),d2
 move.w 10(sp),d3
 eor.w d3,d2
 andi.w #$1f,d2
 bne.b verifybad
 lea verified(pc),a0
 addq.l #1,(a0)
 bra.b verifyend
verifybad:
 lea error(pc),a0
 addq.l #1,(a0)
verifyend:
 move.w (sp)+,ccr
 lea 12(sp),sp
 movem.l (sp)+,d2-d7/a0-a1
 rts
originaldiv:
 incbin "original_div.bin"
modeval: dc.w MODE
installed: dc.l 0
error: dc.l 0
ticks: dc.l 0
verified: dc.l 0
cache_api: dc.l 0
cache_old: dc.l 0
cache_called: dc.l 0
'''
# Correct verifier stack layout: initial SR (2), original SR (2), results (8), candidate SR (2).
for mode,name in enumerate(('control','fast','verify','cache')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)).replace('NORMALSIZE',str(len(base)-36)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base);normal=code[32:-4];pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 size=len(normal);normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/(name+'.bin')).read_bytes();normal+=b'\0'*((-len(normal))%4)
 code[20:24]=struct.pack('>I',len(normal)//4);code[28:32]=code[20:24];(o/(name+'.slave')).write_bytes(code[:32]+normal+bytes.fromhex('000003f2'))
print('Built equal-layout division and omission diagnostics')

a=(o/'control.slave').read_bytes()
for n in ('fast','verify','cache'):
 b=(o/(n+'.slave')).read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1,n
