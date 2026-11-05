from pathlib import Path
import struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-math-v6';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-math-v5/combined.s').read_text().replace('modeval: dc.w 5','modeval: dc.w MODE')
asm=asm.replace(' cmpi.w #5,d0\n bne.b multiply',' cmpi.w #5,d0\n blo.b multiply').replace(' cmpi.w #5,d0\n bne.w extra_done',' cmpi.w #5,d0\n blo.w extra_done')
asm=asm.replace(' bsr.w install_extras\n', ''' bsr.w install_extras
 cmpi.w #6,d0
 bne.b keep_gauges
 cmpi.l #$4a790003,$6bcc8
 bne.w gauge_bad
 cmpi.w #$2b76,$6bccc
 bne.w gauge_bad
 cmpi.l #$302e000a,$6bf26
 bne.w gauge_bad
 cmpi.w #$48c0,$6bf2a
 bne.w gauge_bad
 move.w #$4ef9,$6bcc8
 move.l #$6be6a,$6bcca
 move.w #$4ef9,$6bf26
 move.l #$6bf60,$6bf28
 bra.b keep_gauges
gauge_bad:
 lea error(pc),a1
 move.l #3,(a1)
keep_gauges:
''')
(o/'original_div.bin').write_bytes((r/'tmp/build/step5-math-v5/original_div.bin').read_bytes())
for mode,name in ((5,'control'),(6,'logic')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 normal=bytearray(base[32:-4]);size=len(normal);pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/(name+'.bin')).read_bytes();normal+=b'\0'*((-len(normal))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(normal)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+normal+bytes.fromhex('000003f2'))
a=(o/'control.slave').read_bytes();b=(o/'logic.slave').read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
print('Built equal-layout gauge extraction diagnostics')
