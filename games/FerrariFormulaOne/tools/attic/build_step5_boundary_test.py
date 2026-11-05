from pathlib import Path
import struct,subprocess,json,hashlib,random
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-boundary-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
s=(r/'tools/build_step5_position_test.py').read_text();prefix=s[s.index("prefix='''")+10:s.index("'''\ncases=[]")]
m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes();n=struct.unpack_from('>H',m,0x2268c)[0];angles=struct.unpack_from('>'+str(n)+'h',m,0x1dc24);sn=struct.unpack_from('>1024h',m,0x2180c);cs=struct.unpack_from('>1024h',m,0x21a0c)
cases=[];vectors=[]
def add(x,z,rx,rz,s,c,kind):
 t=((x*5+rx)*s+((z-(512<<16))*5+rz)*c)
 expected=[0,0xffffffff] if not c else [int(t>=0 if c>0 else t<=0),0]
 cases.append(dict(kind=kind,x=x,z=z,rx=rx,rz=rz,s=s,c=c,expected=expected))
 vectors.append(struct.pack('>ihihhh',x,rx,z,rz,s,c))
for i,a in enumerate(angles):
 s=(sn[a&1023]*1000)//32768;c=(cs[a&1023]*1000)//32768
 x=((i%701)-350)*65536+((i*997)%65536);rx=i%9-4
 # Cross the exact rational boundary in the smallest stored tail unit.
 ztail=(512*65536*5)-((x*5+rx)*s)//c
 for offset in (-1,0,1):
  tail=ztail+offset;z=tail//5;rz=tail-z*5
  add(x,z,rx,rz,s,c,'demo_boundary')
for c in (-32768,-1,0,1,32767):
 for s in (-32768,0,32767):
  for x in (-0x80000000,0,0x7fffffff):
   for z in (-0x80000000,512<<16,0x7fffffff):add(x,z,-4,4,s,c,'limits')
for c in (-1000,1000):
 for rx in (-4,0,4):
  for rz in (-1,0,1):add(0,512<<16,rx,rz,0,c,'exact_plane')
asm=prefix+''' lea (vectors.l,pc),a3
 lea (results.l,pc),a4
 move.w #COUNT-1,d7
boundary_loop:
 move.l a3,a0
 move.w 12(a3),d0
 move.w 14(a3),d1
 bsr.w FF1PositionCrossed020
 move.l d0,(a4)+
 move.l d1,(a4)+
 adda.w #16,a3
 dbra d7,boundary_loop
 rts
'''.replace('COUNT',str(len(cases)))
for module in ('Math','Step','Position'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
asm+='installed: dc.l 0\nvectors: incbin "vectors.bin"\nresults: ds.l '+str(len(cases)*2)+'\n'
(o/'vectors.bin').write_bytes(b''.join(vectors));name='fine';(o/(name+'.s')).write_text(asm);(o/(name+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'exact fractional boundary cases')
