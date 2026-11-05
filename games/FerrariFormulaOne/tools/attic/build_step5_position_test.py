from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-position-test';o.mkdir(parents=True,exist_ok=True)
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
cases=[]
for initial, values in ((0,[330]*5), (0,[-330]*5), (0,[1]*5+[-1]*5), (-65536,[2,-3,4,-2,7,-8,0]*3), (0x7fffffff,[1]), (-0x80000000,[-1]), (0,[-32768]), (0,[32767]*5)):
 position=initial;rem=0
 for velocity in values:
  total=(velocity<<16)+rem
  delta=(abs(total)//5)*(1 if total>=0 else -1)
  overflow=not -0x80000000<=total<=0x7fffffff or not -0x80000000<=position+delta<=0x7fffffff
  newpos=position if overflow else position+delta
  newrem=rem if overflow else total-delta*5
  cases.append(dict(position=position,rem=rem,velocity=velocity,expected=[newpos&0xffffffff,newrem&0xffffffff,0xffffffff if overflow else 0]))
  position,rem=newpos,newrem
asm=prefix
for i,c in enumerate(cases):
 asm+=f" lea state(pc),a0\n move.l #${c['position']&0xffffffff:08x},(a0)\n move.w #{c['rem']},4(a0)\n move.w #{c['velocity']},d0\n bsr.w FF1Position20\n lea results+{i*12}(pc),a1\n move.l (a0),(a1)+\n move.w 4(a0),d2\n ext.l d2\n move.l d2,(a1)+\n move.l d1,(a1)\n"
asm+=' rts\n'
for module in ('Math','Step','Position'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
asm+='installed: dc.l 0\nstate: ds.w 3\nresults: ds.l '+str(len(cases)*3)+'\n'
name='fine'
(o/(name+'.s')).write_text(asm);(o/(name+'.json')).write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(normal)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),"position integration cases")
