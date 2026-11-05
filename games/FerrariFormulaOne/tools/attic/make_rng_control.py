#!/usr/bin/env python3
"""Append a one-shot RNG control to a local slave copy; never a release artifact."""
from pathlib import Path
import os,struct,subprocess,json,hashlib
root=Path(__file__).resolve().parents[1]
out=root/'tmp/build/rng-control';out.mkdir(parents=True,exist_ok=True)
b=(root/'tmp/baseline/shipped-c0-valid/race-0.bin').read_bytes()
lines=['start:',' movem.l d0-a6,-(a7)',' move.w sr,-(a7)',' lea flag(pc),a0',' tst.b (a0)',' bne.w original',' st flag']
# ST uses absolute relocation in a raw stub; use LEA PC-relative instead.
lines[-1]=' lea flag(pc),a0\n st (a0)'
for lo,hi in ((0x24f60,0x24fd8),(0x1c8ac,0x1c8ae),(0x66f94,0x66f96)):
 for at in range(lo,hi,2):lines.append(f' move.w #${int.from_bytes(b[at:at+2],"big"):04x},${at:x}.l')
lines += ['original:',' move.w (a7)+,ccr',' movem.l (a7)+,d0-a6',' asl.w #1,d0',' ext.l d0',' move.l d0,a4',' rts','flag: dc.b 0',' even']
(out/'control.s').write_text('\n'.join(lines)+'\n')
subprocess.run([os.environ.get('VASM',str(Path.home()/'.local/vasmm68k_mot')),'-m68000','-Fbin','-quiet','-o',str(out/'control.bin'),str(out/'control.s')],check=True)
stub=(out/'control.bin').read_bytes()
for name,src in [('shipped',root/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/FerrariFormulaOne.slave'),('release',root/'tmp/build/release/FerrariFormulaOne.slave')]:
 data=bytearray(src.read_bytes());size=struct.unpack_from('>I',data,28)[0]*4
 assert len(data)==size+36 and data[-4:]==bytes.fromhex('000003f2')
 pos=data.index(bytes.fromhex('e34048c02840'))-32
 code=data[32:32+size];disp=len(code)-(pos+2)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',disp)+bytes.fromhex('4e71')
 code+=stub;code+=b'\0'*((-len(code))%4)
 data[20:24]=struct.pack('>I',len(code)//4);data[28:32]=data[20:24]
 dest=out/f'{name}.slave';dest.write_bytes(data[:32]+code+bytes.fromhex('000003f2'))
 print(name,hashlib.sha256(dest.read_bytes()).hexdigest())
