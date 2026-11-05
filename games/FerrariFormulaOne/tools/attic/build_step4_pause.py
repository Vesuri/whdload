from pathlib import Path
import hashlib,struct,subprocess
r=Path(__file__).resolve().parents[1];out=r/'tmp/build/step4-pause';out.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
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
 cmpi.l #$4eb90002,$654e6
 bne.w bad
 cmpi.w #$a130,$654ea
 bne.w bad
 cmpi.l #$70ff4e5e,$236b0
 bne.w bad
 cmpi.w #$4e75,$236b4
 bne.w bad
 addq.l #1,(a0)
 lea barrier(pc),a0
 move.l a0,$654e8
 move.w #$4ef9,$236b0
 lea keyread(pc),a0
 move.l a0,$236b2
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
 movem.l d0/a0,-(sp)
 move.w sr,-(sp)
 lea ticks(pc),a0
 addq.l #1,(a0)
 cmpi.l #125,(a0)
 bne.b finish
 lea event(pc),a0
 move.w #1,(a0)
finish:
 move.w (sp)+,ccr
 movem.l (sp)+,d0/a0
 rts
keyread:
 movem.l d1/a0,-(sp)
 lea event(pc),a0
 cmpi.w #1,(a0)
 beq.b first
 cmpi.w #2,(a0)
 bne.b nokey
 move.w $24ad2,d1
 sub.w 2(a0),d1
 cmpi.w #120,d1
 blo.b nokey
 move.w #3,(a0)
 bra.b emit
first:
 move.w #2,(a0)
 move.w $24ad2,2(a0)
emit:
 movem.l (sp)+,d1/a0
 move.l #$45,-4(a6)
 jmp $236d8
nokey:
 movem.l (sp)+,d1/a0
 moveq #-1,d0
 unlk a6
 rts
installed: dc.l 0
error: dc.l 0
ticks: dc.l 0
event: dc.w 0,0
'''
(out/'pause.s').write_text(asm)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L',str(out/'pause.list'),'-o',str(out/'pause.bin'),str(out/'pause.s')],check=True)
code=bytearray(base);normal=code[32:-4];pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
size=len(normal);normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(out/'pause.bin').read_bytes();normal+=b'\0'*((-len(normal))%4)
code[20:24]=struct.pack('>I',len(normal)//4);code[28:32]=code[20:24]
(out/'pause.slave').write_bytes(code[:32]+normal+bytes.fromhex('000003f2'))
