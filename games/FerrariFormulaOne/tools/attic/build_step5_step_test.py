from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-step-test';o.mkdir(parents=True,exist_ok=True)
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
for name in ('fine','coarse'):
 cases=[]
 if name=='fine':
  for values,rem in (([330<<16]*5,0),([-330<<16]*5,0),([1]*5+[-1]*5,0),([2,-3,4,-2,7,-8,0]*3,0),([0x7fffffff],4),([-0x80000000],-4),([0x7fffffff,-0x80000000],0)):
   for value in values:
    total=value+rem;overflow=not -0x80000000<=total<=0x7fffffff
    q=value if overflow else (abs(total)//5)*(1 if total>=0 else -1)
    newrem=rem if overflow else total-5*q
    cases.append({'period':20,'input':value,'initial_remainder':rem,'expected':[q&0xffffffff,0xffffffff if overflow else 0,newrem&0xffffffff]});rem=newrem
 for value in (0,1,-1,330<<16,-330<<16,0x3fffffff,0x40000000,-0x40000000,-0x40000001,0x7fffffff,-0x80000000):
  overflow=not -0x80000000<=value*2<=0x7fffffff
  cases.append({'period':200,'input':value,'initial_remainder':0,'expected':[(value if overflow else value*2)&0xffffffff,0xffffffff if overflow else 0,0]})
 asm=prefix
 for i,c in enumerate(cases):
  asm+=f''' lea remainder(pc),a0
 move.w #{c['initial_remainder']},(a0)
 move.l #${c['input']&0xffffffff:08x},d0
 bsr.w FF1Step{c['period']}Delta
 lea results+{i*12}(pc),a1
 move.l d0,(a1)+
 move.l d1,(a1)+
 move.w (a0),d2
 ext.l d2
 move.l d2,(a1)
'''
 asm+=' rts\n'
 for module in ('Math','Step'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
 asm+='installed: dc.l 0\nremainder: dc.w 0\nresults: ds.l '+str(len(cases)*3)+'\n'
 (o/(name+'.s')).write_text(asm);(o/(name+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(normal)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
 print(name,len(cases),'fraction/reversal/overflow cases')
