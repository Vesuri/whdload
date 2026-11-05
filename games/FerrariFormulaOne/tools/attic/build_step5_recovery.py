from pathlib import Path
import struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-recovery-v3';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step4-v2/logic.s').read_text()
a=asm.index(' cmpi.l #126,(a0)');b=asm.index(' move.w #$4ef9,$65714',a)
asm=asm[:a]+''' cmpi.l #126,(a0)
 bne.w finish
 move.w #$fff8,$2268e
 move.w modeval(pc),d0
 tst.w d0
 beq.w finish
'''+asm[b:]
asm=asm.replace(' move.w $66faa,d0',''' move.w modeval(pc),d0
 cmpi.w #2,d0
 bne.b no_recovery
 lea $2268e,a0
 moveq #1,d0
 bsr.w FF1AdvanceRecovery
no_recovery:
 move.w $66faa,d0''')
asm+=' include \"'+str(r.parent.parent/'Games/FerrariFormulaOne_Logic.s')+'\"\n'
asm+='''modeval: dc.w MODE
verified: dc.l 0
cache_called: dc.l 0
cache_api: dc.l 0
cache_old: dc.l 0
'''
for mode,name in enumerate(('control','broken','fixed')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 normal=bytearray(base[32:-4]);size=len(normal);pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/(name+'.bin')).read_bytes();normal+=b'\0'*((-len(normal))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(normal)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+normal+bytes.fromhex('000003f2'))
a=(o/'control.slave').read_bytes()
for name in ('broken','fixed'):
 b=(o/(name+'.slave')).read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
print('Built native recovery, negative control and extracted-recovery diagnostics')
