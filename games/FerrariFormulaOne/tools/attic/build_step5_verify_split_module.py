from pathlib import Path
import re,struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];root=r/'tmp/build/step5-verify-split-module';root.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
for variant in ('verify','lean'):
 prior=r/'tmp/build/step5-verify-split-v4'/variant
 source=(prior/'fine.s').read_text();a=source.index('install_velocity:\n');b=source.index('selection_boot:\n');tail=source.index(' IFND VERIFY\nvelocity_scratch equ velocity_records')
 source=source[:a]+' include "FerrariFormulaOne_UpdateHooks.s"\n'+source[b:tail]+' FF1UpdateWorkspace\n'
 o=root/variant;o.mkdir(parents=True,exist_ok=True);(o/'fine.s').write_text(source);(o/'original_div.bin').write_bytes((prior/'original_div.bin').read_bytes())
 args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','fine.list','-o','fine.bin']
 if variant=='verify':args+=['-DVERIFY=1']
 subprocess.run(args+['fine.s'],cwd=o,check=True)
 assert (o/'fine.bin').read_bytes()==(prior/'fine.bin').read_bytes(),variant+' extraction changed code'
 (o/'fine.slave').write_bytes((prior/'fine.slave').read_bytes())
 print(variant,'module machine code identical',hashlib.sha256((o/'fine.bin').read_bytes()).hexdigest())
