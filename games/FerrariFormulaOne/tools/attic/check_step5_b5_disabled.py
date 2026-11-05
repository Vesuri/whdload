from pathlib import Path
import re,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];out=r/'tmp/build/step5-b5-disabled';out.mkdir(parents=True,exist_ok=True)
result={}
for variant in ('verify','lean'):
 ref=r/f'tmp/build/step5-b4-v4/{variant}';o=out/variant;o.mkdir(exist_ok=True)
 for f in ('fine.s','original_div.bin'):(o/f).write_bytes((ref/f).read_bytes())
 args=[str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-DFF1_PLAN_B=1','-DFF1_PLAYER_HOOKS=1','-L','fine.list','-o','fine.bin']
 if variant=='verify':args+=['-DVERIFY=1']
 subprocess.run(args+['fine.s'],cwd=o,check=True)
 assert (o/'fine.bin').read_bytes()==(ref/'fine.bin').read_bytes()
 result[variant]={'byte_identical_b4':True,'bin_sha256':hashlib.sha256((o/'fine.bin').read_bytes()).hexdigest()}
for path,sha in [('Games/FerrariFormulaOne_WHD.s','88995624ab0cc80974109bfede29ff6aa7434cf9901933b1961cf87eda851761'),('tmp/dev/tmp/build/release/FerrariFormulaOne.slave','b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f')]:assert hashlib.sha256((r.parents[1]/path).read_bytes()).hexdigest()==sha
(r/'manifest/step5-b5-disabled-validation.json').write_text(json.dumps(dict(status='passed',variants=result,ordinary_unchanged=True),indent=2)+'\n');print(result)
