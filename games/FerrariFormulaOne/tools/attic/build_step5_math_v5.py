from pathlib import Path
import re,json,struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-math-v5';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-math-v4/control.s').read_text();asm=asm.replace('modeval: dc.w 0','modeval: dc.w MODE')
a=asm.index(' lea FF1Divide000(pc),a1');b=asm.index('plant:',a)
asm=asm[:a]+' lea FF1Divide020(pc),a1\n'+asm[b:]
asm=asm.replace(' cmpi.w #5,d0\n bne.b finish',' bsr.w install_extras\n cmpi.w #2,d0\n blo.w finish')
# Distinct variants identify square-root and inlined-multiply contributions.
extra='''install_extras:
 cmpi.w #3,d0
 beq.b square
 cmpi.w #5,d0
 bne.b multiply
square:
 cmpi.l #$343c0200,$25770
 bne.w extra_bad
 lea FF1SquareRoot020(pc),a1
 move.w #$4ef9,$25770
 move.l a1,$25772
multiply:
 cmpi.w #4,d0
 beq.b check_mul
 cmpi.w #5,d0
 bne.w extra_done
check_mul:
'''
lines=(r/'tmp/step4/active.dis').read_text().splitlines();sites=[];memory=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
for i,l in enumerate(lines):
 if 'jsr $29500.l' not in l:continue
 pc=int(l[:6],16);following=lines[i+1];code=following.split(' ;')[0].split(None,2)[-1]
 safe=bool(re.match(r'(as[lr]|ls[lr])\.[bwl] #',code) or re.match(r'(add|sub|addi|subi|addq|subq|neg)\.[bwl] ',code) and not re.search(r', a[0-7]$',code))
 if not safe and 'moveq #' in code:
  m=re.match(r'moveq #\$([0-9a-f]+), d1$',code)
  safe=bool(m and 0<int(m[1],16)<64 and re.match(r'(as[lr]|ls[lr])\.[bwl] d1, d0',lines[i+2].split(' ;')[0].split(None,2)[-1]))
 if not safe:continue
 signature=memory[pc:pc+12];assert signature[:6]==bytes.fromhex('4eb900029500')
 sites.append({'pc':hex(pc),'signature':signature.hex(),'flag_overwrite':following,'following':lines[i+2]})
 for j in (0,4,8):extra+=f' cmpi.l #${signature[j:j+4].hex()},${pc+j:x}\n bne.w extra_bad\n'
for site in sites:
 pc=int(site['pc'],16);extra+=f' move.l #$4c010800,${pc:x}\n move.w #$4e71,${pc+4:x}\n'
extra+='''extra_done:
 rts
extra_bad:
 lea error(pc),a1
 move.l #2,(a1)
 rts
'''
extra+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Sqrt.s')+'"\n'
asm=asm.replace('verifydiv:',extra+'verifydiv:')
(o/'original_div.bin').write_bytes((r/'tmp/build/step5-math-v4/original_div.bin').read_bytes())
(o/'inline-sites.json').write_text(json.dumps(sites,indent=2)+'\n')
for mode,name in enumerate(('control','div','cache','sqrt','multiply','combined')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 normal=bytearray(base[32:-4]);size=len(normal);pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/(name+'.bin')).read_bytes();normal+=b'\0'*((-len(normal))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(normal)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+normal+bytes.fromhex('000003f2'))
a=(o/'control.slave').read_bytes()
for name in ('div','cache','sqrt','multiply','combined'):
 b=(o/(name+'.slave')).read_bytes();assert len(a)==len(b) and sum(x!=y for x,y in zip(a,b))==1
print('Built six equal-layout variants;',len(sites),'multiply sites with dead original flags')
