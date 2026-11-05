from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-clamp-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
s=(r/'tools/build_step5_position_test.py').read_text();prefix=s[s.index("prefix='''")+10:s.index("'''\ncases=[]")]
cases=[];vectors=[]
for lower in (True,False):
 for bound in (-32768,-350,0,350,32767):
  for integer in (bound-1,bound,bound+1):
   if not -32768<=integer<=32767:continue
   for fraction in (0,1,65535):
    for rem in (-4,0,4):
     q=integer*65536+fraction;value=q*5+rem;limit=bound*65536*5;clamp=value<limit if lower else value>limit
     expected=[((bound*65536) if clamp else q)&0xffffffff,0 if clamp else rem&0xffffffff,int(clamp)]
     cases.append(dict(lower=lower,bound=bound,integer=integer,fraction=fraction,remainder=rem,expected=expected))
     vectors.append(struct.pack('>ihhh',q,rem,bound,int(lower)))
asm=prefix+''' lea vectors(pc),a3
 lea results(pc),a4
 move.w #COUNT-1,d7
clamp_loop:
 lea state(pc),a0
 move.l (a3)+,(a0)
 move.w (a3)+,4(a0)
 move.w (a3)+,d0
 tst.w (a3)+
 beq.b upper
 bsr.w FF1PositionClampLower
 bra.b save
upper:
 bsr.w FF1PositionClampUpper
save:
 move.l (a0),(a4)+
 move.w 4(a0),d2
 ext.l d2
 move.l d2,(a4)+
 move.l d1,(a4)+
 dbra d7,clamp_loop
 rts
'''.replace('COUNT',str(len(cases)))
for module in ('Math','Step','Position'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
asm+='installed: dc.l 0\nstate: ds.w 3\nvectors: incbin "vectors.bin"\nresults: ds.l '+str(len(cases)*3)+'\n'
(o/'vectors.bin').write_bytes(b''.join(vectors));name='fine';(o/(name+'.s')).write_text(asm);(o/(name+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'fractional clamp cases')
