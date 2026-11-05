from pathlib import Path
import subprocess,struct
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b7-memory';o.mkdir(parents=True,exist_ok=True)
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
 lea results(pc),a4
 move.l d0,(a4)+
 move.l #$10000,d0
 bsr.w FF1PublicPoolOpen
 move.l d0,(a4)+
 lea owner(pc),a0
 move.l #$5000,d0
 bsr.w FF1PublicAcquire
 move.l d0,(a4)+
 move.l d0,a1
 move.l #$12345678,(a1)
 move.l #$87654321,$4ffc(a1)
 moveq #16,d0
 bsr.w FF1PublicAcquire
 move.l d0,(a4)+
 bsr.w FF1PublicRelease
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 bsr.w FF1PublicRelease
 move.l #$5000,d0
 bsr.w FF1PublicAcquire
 move.l d0,(a4)+
 bsr.w FF1PublicRelease
 move.l #$10000000,d0
 bsr.w FF1PublicAcquire
 move.l d0,(a4)+
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 rts
installed: dc.l 0
pool: ds.l 2
owner: ds.l 2
results: ds.l 10
 include "FerrariFormulaOne_PublicMemory.s"
'''
(o/'memory.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_PUBLIC_MEMORY=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','memory.list','-o','memory.bin','memory.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);code[0x20:0x24]=struct.pack('>I',0x50000);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'memory.bin').read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'memory.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
print('Built 68000-safe public memory fixture')
