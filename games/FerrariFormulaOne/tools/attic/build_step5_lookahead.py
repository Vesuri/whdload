from pathlib import Path
import struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-lookahead';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-math-v6/logic.s').read_text().replace('modeval: dc.w 6','modeval: dc.w MODE').replace(' cmpi.w #6,d0\n bne.b keep_gauges',' cmpi.w #6,d0\n blo.b keep_gauges')
asm=asm.replace(' cmpi.l #126,(a0)\n', ''' cmpi.l #100,(a0)
 bne.b no_oracle
 bsr.w check_track
 lea ticks(pc),a0
no_oracle:
 cmpi.l #126,(a0)
''')
asm=asm.replace('keep_gauges:\n', '''keep_gauges:
 cmpi.w #7,d0
 bne.b no_track_patch
 lea track_hook(pc),a1
 move.w #$4ef9,$6977a
 move.l a1,$6977c
no_track_patch:
''')
asm+='''
check_track:
 tst.w $1ed8a
 bne.w track_bad
 cmpi.w #12,$2268c
 blo.w track_bad
 cmpi.w #32767,$2268c
 bhi.w track_bad
 moveq #0,d6
oracle_loop:
 move.l d6,-(sp)
 jsr $6977a
 addq.l #4,sp
 move.l d0,d7
 move.l d6,d0
 moveq #0,d1
 move.w $2268c,d1
 lea $1dc24,a0
 bsr.w FF1TrackLookaheadNormal
 cmp.l d7,d0
 bne.b track_bad
 lea track_verified(pc),a0
 addq.l #1,(a0)
 addq.l #1,d6
 cmp.w $2268c,d6
 blo.b oracle_loop
 rts
track_bad:
 lea error(pc),a0
 move.l #5,(a0)
 rts
track_hook:
 tst.w $1ed8a
 bne.w native_track
 moveq #0,d1
 move.w $2268c,d1
 cmpi.l #12,d1
 blo.w native_track
 cmpi.l #32767,d1
 bhi.w native_track
 move.w 6(sp),d0
 ext.l d0
 bmi.w native_track
 cmp.l d1,d0
 bhs.w native_track
 lea $1dc24,a0
 bra.w FF1TrackLookaheadNormal
native_track:
 incbin "original_track.bin"
track_verified: dc.l 0
 include "CORE"
'''.replace('CORE',str(r.parent.parent/'Games/FerrariFormulaOne_Track.s'))
m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes();(o/'original_track.bin').write_bytes(m[0x6977a:0x6988c]);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-math-v6/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'fast')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 normal=bytearray(base[32:-4]);size=len(normal);pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/(name+'.bin')).read_bytes();normal+=b'\0'*((-len(normal))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(normal)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+normal+bytes.fromhex('000003f2'))
a=(o/'control.slave').read_bytes();b=(o/'fast.slave').read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
print('Built normal-mode lookahead value oracle and equal-layout diagnostics')
