from pathlib import Path
import struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-vbl';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step4-v2/logic.s').read_text().replace(' move.w #2,d0',' move.w modeval(pc),d0')
asm=asm.replace(' lea barrier(pc),a0\n move.l a0,$654e8\n bra.w done',''' lea barrier(pc),a0
 move.l a0,$654e8
 move.w modeval(pc),d0
 cmpi.w #3,d0
 beq.w done
 cmpi.l #$33c10002,$24946
 bne.w bad
 cmpi.w #$4ad2,$2494a
 bne.w bad
 lea context(pc),a0
 moveq #20,d0
 bsr.w FF1TimeInit
 move.l $4.w,a6
 jsr -120(a6)
 lea nativebase(pc),a0
 move.w $24ad2,(a0)
 lea vbl(pc),a0
 move.w #$4eb9,$24946
 move.l a0,$24948
 ; Ordinary release has instruction cache disabled. Use the WHDLoad flush
 ; API as well so installation does not rely on that diagnostic property.
 lea start(pc),a2
 suba.l #NORMALSIZE,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 move.l $4.w,a6
 jsr -126(a6)
 bra.w done''')
asm+='''
vbl:
 move.w d1,$24ad2
 movem.l d0-d3/a0-a1,-(sp)
 move.w sr,-(sp)
 lea context(pc),a0
 bsr.w FF1TimeField
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 rts
modeval: dc.w MODE
nativebase: dc.w 0
verified: dc.l 0
cache_called: dc.l 0
cache_api: dc.l 0
cache_old: dc.l 0
 include "CORE"
context: ds.b FF1T_SIZE
'''
asm=asm.replace('CORE',str(r.parent.parent/'Games/FerrariFormulaOne_Time.s')).replace('NORMALSIZE',str(len(base)-36))
for mode,name in enumerate(('control','slow','logic','off')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 normal=bytearray(base[32:-4]);size=len(normal);pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/(name+'.bin')).read_bytes();normal+=b'\0'*((-len(normal))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(normal)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+normal+bytes.fromhex('000003f2'))
a=(o/'control.slave').read_bytes()
for name in ('slow','logic','off'):
 b=(o/(name+'.slave')).read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
print('Built equal-layout VBL clock / drawing diagnostics')
