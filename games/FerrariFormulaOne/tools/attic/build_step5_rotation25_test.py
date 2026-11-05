from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-rotation25-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix='''start:
 add.l $1c(a3),d0
 move.l d0,a1
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 cmp.l #$64a68,d0
 bne.w done
 lea installed(pc),a0
 tst.l (a0)
 bne.w done
 addq.l #1,(a0)
 lea barrier(pc),a0
 move.l a0,$654e8
 bsr.w tests
done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
barrier: jmp $2a130
tests:
'''
memory=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
sines=struct.unpack_from('>1024h',memory,0x2180c)
cosines=struct.unpack_from('>1024h',memory,0x21a0c)
cases=[];records=[]
inputs=[(angle,x,z,rx,rz,nx,nz) for angle in range(1024)
 for x,z,rx,rz,nx,nz in ((0,0,0,0,123,-456),(65535,65535,24,-24,123,-456),(1,32768,-24,23,-1,512))]
inputs += [(angle,65535,65535,24,24,nx,nz) for angle in (128,384,640,896)
 for nx,nz in ((32767,32767),(-32768,-32768))]
inputs += [(angle,0,0,-24,-24,0,0) for angle in (0,1,128,256,512,768)]
for angle,x,z,rx,rz,nx,nz in inputs:
 c,s=cosines[angle],sines[angle]
 tx,tz=x*25+rx,z*25+rz
 tails=((tx*c-tz*s)//32768,(tx*s+tz*c)//32768)
 new=[];overflow=False
 for native,tail in zip((nx,nz),tails):
  q=(abs(tail)//25)*(1 if tail>=0 else -1)
  pos=(native<<16)+q
  overflow |= not -0x80000000<=pos<=0x7fffffff
  new.extend([pos&0xffffffff,(tail-q*25)&0xffffffff])
 expected=[x,rx&0xffffffff,z,rz&0xffffffff,0xffffffff] if overflow else new+[0]
 cases.append(dict(angle=angle,overflow=overflow,expected=expected))
 records.append(struct.pack('>HHhHHhhhhhh',0,x,rx,0,z,rz,c,s,nx,nz,0))
# Fixed-size data-driven guest fixture avoids thousands of expanded call sites.
asm=prefix+""" lea vectors(pc),a3
 lea results(pc),a4
 move.w #COUNT-1,d7
rotation_loop:
 lea state(pc),a0
 move.l (a3)+,(a0)
 move.w (a3)+,4(a0)
 move.l (a3)+,6(a0)
 move.w (a3)+,10(a0)
 move.w (a3)+,d0
 move.w (a3)+,d1
 move.w (a3)+,d2
 move.w (a3)+,d3
 addq.l #2,a3
 bsr.w FF1PositionRotate25
 move.l (a0),(a4)+
 move.w 4(a0),d2
 ext.l d2
 move.l d2,(a4)+
 move.l 6(a0),(a4)+
 move.w 10(a0),d2
 ext.l d2
 move.l d2,(a4)+
 move.l d1,(a4)+
 dbra d7,rotation_loop
 rts
""".replace('COUNT',str(len(cases)))
for module in ('Math','Step','Position'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
# Large tables use 020 long PC-relative addressing for the two initial LEAs.
asm=asm.replace('lea vectors(pc),a3','lea (vectors.l,pc),a3').replace('lea results(pc),a4','lea (results.l,pc),a4')
asm+='installed: dc.l 0\nstate: ds.w 6\nvectors: incbin "vectors.bin"\nresults: ds.l '+str(len(cases)*5)+'\n'
(o/'vectors.bin').write_bytes(b''.join(records))
name='fine'
(o/(name+'.s')).write_text(asm);(o/(name+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(normal)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),"fractional rotation cases")
