from pathlib import Path
import hashlib,struct,subprocess,json
r=Path(__file__).resolve().parents[1];out=r/'tmp/build/step4-contact-v3';out.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm_template="""start:
 add.l $1c(a3),d0
 move.l d0,a1
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 cmp.l #$64a68,d0
 bne.w done
 lea installed(pc),a0
 tst.l (a0)
 bne.w done
 cmpi.l #$4eb90002,$654e6
 bne.w bad
 cmpi.w #$a130,$654ea
 bne.w bad
 addq.l #1,(a0)
 lea barrier(pc),a0
 move.l a0,$654e8
 lea collision_input(pc),a0
 move.w #$4eb9,$68292
 move.l a0,$68294
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
 blo.w finish
 move.w #MODE,d0
 cmpi.w #1,d0
 bne.b test_logic
 moveq #2,d7
 move.l $4.w,a6
 move.l $9c(a6),a6
slow:
 jsr -270(a6)
 dbra d7,slow
 bra.b finish
test_logic:
 cmpi.l #126,(a0)
 bne.w finish
 lea contact_pending(pc),a1
 move.l #1,(a1)
 cmpi.w #4,d0
 bne.w finish
 move.w #$4ef9,$65714
 lea logic_tail(pc),a1
 move.l a1,$65716
 move.w #$4ef9,$65f2e
 move.l #$65174,$65f30
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
collision_input:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 lea contact_pending(pc),a0
 tst.l (a0)
 beq.b contact_done
 tst.w $32fbc
 bne.b contact_done
 clr.l (a0)
 move.w $32fca,d0
 add.w d0,d0
 lea $1c914,a0
 move.w (a0,d0.w),d0
 neg.w d0
 subi.w #80,d0
 move.w d0,$32fc2
contact_done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 move.w $32fbc,d0
 rts
contact_pending: dc.l 0
installed: dc.l 0
error: dc.l 0
ticks: dc.l 0
"""
for mode,name in ((3,'control'),(4,'logic')):
 asm=asm_template.replace('MODE',str(mode));(out/(name+'.s')).write_text(asm)
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L',str(out/(name+'.list')),'-o',str(out/(name+'.bin')),str(out/(name+'.s'))],check=True)
 code=bytearray(base);normal=code[32:-4];pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 stub=(out/(name+'.bin')).read_bytes();size=len(normal)
 normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=stub;normal+=b'\0'*((-len(normal))%4)
 code[20:24]=struct.pack('>I',len(normal)//4);code[28:32]=code[20:24]
 (out/(name+'.slave')).write_bytes(code[:32]+normal+bytes.fromhex('000003f2'))
a=(out/'control.slave').read_bytes()
for name in ('logic',):
 b=(out/(name+'.slave')).read_bytes();assert len(a)==len(b);assert sum(x!=y for x,y in zip(a,b))==1
print('Equal-size control, delayed drawing and logic diagnostic built; one mode byte differs')
