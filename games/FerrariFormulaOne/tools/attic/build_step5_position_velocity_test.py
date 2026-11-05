from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-position-velocity-test';o.mkdir(parents=True,exist_ok=True)
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
for initial, rem in ((0,0),(1,-24),(-1,24),(2**31-1,0),(-2**31,0),(1234567,3)):
 for velocity in (-2**31,-65537,-1,0,1,65537,2**31-1):
  for vr in (-4,0,4):
   total=5*velocity+vr+rem;delta=(abs(total)//25)*(1 if total>=0 else -1)
   overflow=not -2**31<=initial+delta<2**31
   cases.append(dict(position=initial,rem=rem,velocity=velocity,vr=vr,expected=[(initial if overflow else initial+delta)&0xffffffff,(rem if overflow else total-delta*25)&0xffffffff,0xffffffff if overflow else 0]))
for initial,rem,velocity,vr in ((0,25,0,0),(0,-25,0,0),(0,0,0,5),(0,0,0,-5)):
 cases.append(dict(position=initial,rem=rem,velocity=velocity,vr=vr,expected=[initial&0xffffffff,rem&0xffffffff,0xffffffff]))
asm=prefix
for i,c in enumerate(cases):
 asm+=f" lea state(pc),a0\n move.l #${c['position']&0xffffffff:08x},(a0)\n move.w #{c['rem']},4(a0)\n move.l #{c['velocity']},d0\n move.w #{c['vr']},d1\n bsr.w FF1Position20Velocity\n lea results+{i*12}(pc),a1\n move.l (a0),(a1)+\n move.w 4(a0),d2\n ext.l d2\n move.l d2,(a1)+\n move.l d1,(a1)\n"
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
