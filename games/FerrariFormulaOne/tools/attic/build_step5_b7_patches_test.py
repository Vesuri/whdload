from pathlib import Path
import subprocess,struct,os
r=Path(__file__).resolve().parents[1];o=r/('tmp/build/step5-b7-patches-'+os.environ.get('PATCH_CASE','normal'));o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
s=prefix+''' lea start(pc),a1
 suba.l #5440,a1
 move.l $20(a1),a1
 adda.l #$40000,a1
 lea pool(pc),a0
 move.l #$10000,d0
 moveq #1,d1
 move.l a1,d2
 cmpi.l #$200000,d2
 blo.b .attributes
 cmpi.l #$a00000,d2
 bhs.b .attributes
 moveq #5,d1
.attributes:
 bsr.w FF1PublicPoolOpen
 lea table(pc),a0
 lea hunk_a+4(pc),a1
 move.l a1,d0
 lsr.l #2,d0
 move.l d0,(a0)+
 lea hunk_b+4(pc),a1
 move.l a1,d0
 lsr.l #2,d0
 move.l d0,(a0)
 lea results(pc),a6
 lea context(pc),a0
 lea table(pc),a1
 bsr.w FF1PatchBegin
 move.l d0,(a6)+
 lea hunk_a+8(pc),a2
 move.w #$9876,(a2)
 lea hunk_b+8(pc),a2
 move.w #$abcd,(a2)
 bsr.w FF1PatchSeal
 move.l d0,(a6)+
 move.l context+16(pc),(a6)+
 bsr.w FF1PatchBegin
 move.l d0,(a6)+
 lea hunk_a+8(pc),a2
 move.w #$3333,(a2)
 move.w #$4444,2(a2)
 bsr.w FF1PatchSeal
 move.l d0,(a6)+
 move.l context+16(pc),(a6)+
 move.l hunk_a+8(pc),(a6)+
 bsr.w FF1PatchRestore
 move.l d0,(a6)+
 move.l hunk_a+8(pc),(a6)+
 move.l hunk_b+8(pc),(a6)+
 move.l context(pc),(a6)+
 move.l context+8(pc),(a6)+
 move.l context+16(pc),(a6)+
 bsr.w FF1PatchRestore
 move.l d0,(a6)+
 rts
installed: dc.l 0
pool: ds.l 2
context: ds.l 6
results: ds.l 14
 cnop 0,4
table: ds.l 2
hunk_a: dc.l 40,0,$12345678,1,2,3,4,5,6,7
hunk_b: dc.l 40,0,$87654321,8,9,10,11,12,13,14
 include "FerrariFormulaOne_PublicMemory.s"
 include "FerrariFormulaOne_PublicPatches.s"
'''
(o/'memory.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_PUBLIC_MEMORY=1','-DFF1_PUBLIC_PATCHES=1','-DFF1_PATCH_HUNKS=2','-DFF1_PATCH_LEDGER_BYTES='+('12' if os.environ.get('PATCH_CASE')=='overflow' else '48'),'-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','memory.list','-o','memory.bin','memory.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);code[0x20:0x24]=struct.pack('>I',0x50000);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'memory.bin').read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'memory.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
print('Built 68000-safe public memory fixture')
