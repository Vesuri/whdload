from pathlib import Path
import struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-selection';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
normal=bytearray(base[32:-4]);size=len(normal);entry=struct.unpack_from('>H',normal,24)[0]
asm='''start:
 add.l $1c(a3),d0
 move.l d0,a1
 movem.l d0-d1/a0,-(sp)
 move.w sr,-(sp)
 cmpi.l #$64a68,d0
 bne.b .done
 lea barrier(pc),a0
 move.l a0,$654e8
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d1/a0
 rts
barrier:
 jmp $2a130
selection_boot:
 movem.l d0-d7/a0-a6,-(sp)
 move.l a0,a2
 lea selection_tags(pc),a0
 jsr $34(a2)
 move.l selection_custom2(pc),d0
 move.l selection_attn(pc),d1
 lea start(pc),a0
 suba.l #SIZE,a0
 move.l $20(a0),d2
 move.l #$40000,d3
 lea selection_expansion(pc),a1
 move.l d2,(a1)
 bsr.w FF1SelectProfile
 lea selection_path(pc),a0
 move.l d0,(a0)+
 move.l d1,(a0)
 movem.l (sp)+,d0-d7/a0-a6
 ; Original entry immediately overwrites A1; other boot inputs preserved.
 lea start(pc),a1
 suba.l #BACK,a1
 jmp (a1)
selection_tags: dc.l $88000000
selection_attn: dc.l 0
 dc.l $88000008
selection_custom2: dc.l 0
 dc.l 0
selection_expansion: dc.l 0
selection_path: dc.l 0
selection_interval: dc.l 0
selection_enabled: dc.l 0
 include "CORE"
'''.replace('SIZE',str(size)).replace('BACK',str(size-entry)).replace('CORE',str(r.parent.parent/'Games/FerrariFormulaOne_Profile.s'))
(o/'fine.s').write_text(asm)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
import re
listing=(o/'fine.list').read_text();boot=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16)
struct.pack_into('>H',normal,24,size+boot)
pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6)
normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/'fine.bin').read_bytes();normal+=b'\0'*((-len(normal))%4)
header=bytearray(base[:32]);struct.pack_into('>I',header,20,len(normal)//4);header[28:32]=header[20:24]
(o/'fine.slave').write_bytes(header+normal+bytes.fromhex('000003f2'))
data=bytearray((o/'fine.slave').read_bytes());at=32+size+10
assert data[at:at+2]==bytes.fromhex('40e7'),data[at:at+2].hex()
data[at:at+2]=bytes.fromhex('42e7');(o/'fine020.slave').write_bytes(data)
print('Built startup profile selection diagnostic; selected paths remain inactive')
