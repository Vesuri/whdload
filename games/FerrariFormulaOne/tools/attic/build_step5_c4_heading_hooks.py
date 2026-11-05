from pathlib import Path
import struct,subprocess,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-c4-heading-hooks';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal)
start=(r/'tmp/build/step5-c3-track-test/track.s').read_text().split('tests:')[0]
sites=[(0x678de,0x32fb4),(0x67900,0x32fb8),(0x67948,0x32fb4),(0x67976,0x32fb8)]
values=[0,1,0xffffffff,0x7fffffff,0x80000000,0x3fffffff,0xc0000000,4095,4096,0x3fffff,0x400000]
def flags(a,b):
 s=(a+b)&0xffffffff;c=int(a+b>0xffffffff);v=int(bool((~(a^b)&(a^s))&0x80000000));return c*17+int(s>=2**31)*8+int(s==0)*4+v*2
for mode in (0,1):
 cases=[]
 for site,target in sites:
  for old in values:
   for delta in values:
    for incoming in (0,31):
     before=(old+delta*mode)&0xffffffff
     cases.append((site,target,old,delta,(before+delta)&0xffffffff,flags(before,delta),incoming))
 (o/f'cases{mode}.bin').write_bytes(b''.join(struct.pack('>7I',*c) for c in cases))
 s=start+'tests:\n move.l $32fb4,-(sp)\n move.l $32fb8,-(sp)\n lea saved(pc),a0\n'
 for site,target in sites:s+=f' move.l ${site:x},(a0)+\n move.l ${site+4:x},(a0)+\n'
 if mode:s+=' bsr.w FF1InstallCoarse200\n'
 for site,target in sites:s+=f' move.w #$4e75,${site+6:x}\n'
 s+=''' lea cases(pc),a4
 move.w #COUNT-1,d7
.loop:
 move.l 4(a4),a0
 move.l 8(a4),(a0)
 move.l 12(a4),d0
 move.l #$12345678,d1
 move.l #$abcdef01,d2
 move.l #$76543210,d3
 move.l (a4),a1
 move.w 26(a4),ccr
 jsr (a1)
 move.w sr,d4
 andi.l #31,d4
 cmp.l 20(a4),d4
 bne.b .bad
 move.l (a0),d4
 cmp.l 16(a4),d4
 bne.b .bad
 cmp.l 12(a4),d0
 bne.b .bad
 cmpi.l #$12345678,d1
 bne.b .bad
 cmpi.l #$abcdef01,d2
 bne.b .bad
 cmpi.l #$76543210,d3
 bne.b .bad
 lea checked(pc),a1
 addq.l #1,(a1)
 adda.w #28,a4
 dbra d7,.loop
 bra.b .finish
.bad:
 lea error(pc),a1
 move.l #1,(a1)
 lea failed_case(pc),a1
 move.l a4,(a1)+
 move.l d4,(a1)+
 move.l (a0),(a1)+
 move.l d7,(a1)+
 move.l d0,(a1)+
.finish:
 lea saved(pc),a0
'''.replace('COUNT',str(len(cases)))
 for site,target in sites:s+=f' move.l (a0)+,${site:x}\n move.l (a0)+,${site+4:x}\n'
 s+=''' move.l (sp)+,$32fb8
 move.l (sp)+,$32fb4
 rts
C1Fault:
 lea error(pc),a0
 move.l #2,(a0)
.stop: bra.b .stop
 include "FerrariFormulaOne_Coarse200.s"
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 5
outputs: ds.b 12
saved: ds.b 32
cases: incbin "CASES"
'''.replace('CASES',f'cases{mode}.bin')
 (o/f'hooks{mode}.s').write_text(s)
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_COARSE_200=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L',f'hooks{mode}.list','-o',f'hooks{mode}.bin',f'hooks{mode}.s'],cwd=o,check=True)
 code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/f'hooks{mode}.bin').read_bytes();code+=b'\0'*((-len(code))%4)
 h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/f'hooks{mode}.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps(dict(comparisons=len(cases),scope='Four installed heading hooks/native controls; modular Q12 values, return paths, registers and full XNZVC'))+'\n')
s=(r/'tools/test_step5_c4_wide.py').read_text().replace('step5-c4-wide','step5-c4-heading-hooks').replace('c4-wide-oracle','c4-heading-hooks').replace("(('a500',1),)","(('a500',0),('a500',1))").replace("'wide.list'","f'hooks{mode}.list'").replace("'wide.slave'","f'hooks{mode}.slave'").replace('FerrariFormulaOne_Wide000.s','FerrariFormulaOne_Coarse200.s')
(r/'tools/test_step5_c4_heading_hooks.py').write_text(s)
print('Built',len(cases),'cases per arm')
