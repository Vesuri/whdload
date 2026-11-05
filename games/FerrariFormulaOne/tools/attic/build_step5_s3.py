from pathlib import Path
import subprocess,struct,re,hashlib,json
r=Path(__file__).resolve().parents[1];base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
for variant in ('verify','lean'):
 for passes in (0,1,3):
  prior=r/'tmp/build/step5-s2-scheduler-fix'/variant;o=r/'tmp/build/step5-s3'/f'{variant}-p{passes}';o.mkdir(parents=True,exist_ok=True)
  s=(prior/'fine.s').read_text()
  a=s.index(' cmpi.w #6,d0');b=s.index('keep_gauges:',a);s=s[:a]+s[b:]
  s=s.replace(' bsr.w install_recovery',' bsr.w install_recovery\n bsr.w FF1InstallPresentation')
  a=s.index('logic_tail:');b=s.index(' include ',a);s=s[:a]+'logic_tail:\n jmp FF1SimulationTail\n'+s[b:]
  a=s.index('selection_boot:');b=s.index('\ns2_rng_control:',a);boot=s[a:b];s=s[:a]+s[b:]
  marker=' include "FerrariFormulaOne_UpdateHooks.s"';s=s.replace(marker,boot+'\n'+marker)
  callback='\nFF1PresentationAfterTick:\n'
  if passes:
   callback+=' movem.l d0-d7/a0-a6,-(sp)\n move.w ccr,-(sp)\n'
   callback+=' bsr.w FF1PresentComponents\n'*passes
   callback+=' move.w (sp)+,ccr\n movem.l (sp)+,d0-d7/a0-a6\n'
  s=s.replace(' FF1UpdateWorkspace',callback+' rts\n FF1UpdateWorkspace')
  (o/'fine.s').write_text(s);(o/'original_div.bin').write_bytes((prior/'original_div.bin').read_bytes())
  args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-L','fine.list','-o','fine.bin']
  if variant=='verify':args+=['-DVERIFY=1']
  subprocess.run(args+['fine.s'],cwd=o,check=True)
  code=bytearray(base[32:-4]);size=len(code);listing=(o/'fine.list').read_text();entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16);assert size+entry<32768
  struct.pack_into('>H',code,24,size+entry);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
  code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
  h=bytearray(base[:32]);struct.pack_into('>I',h,20,len(code)//4);h[28:32]=h[20:24];(o/'fine.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
  print(variant,passes,size+entry,hashlib.sha256((o/'fine.slave').read_bytes()).hexdigest())
