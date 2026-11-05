#!/usr/bin/env python3
from pathlib import Path
import os,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];src=(r/'tmp/build/release/FerrariFormulaOne_WHD.s').read_bytes()
# Same instruction shape, size and allocation in both arms. The word differs only.
# Insert before the existing timing tests overwrite CCR. Applies only to SPS race.
needle=b'; fix wrong blit\n\tmove.w\t#$9240,$6b0ba-$64a68(a1)'
assert src.count(needle)==1
b=(r/'tmp/step3/a500-calibration/anchor.bin').read_bytes();original=b[0x6ac4a:0x6ac4c].hex()
for name,word in [('control',original),('no-road-lines','4e75')]:
 out=r/'tmp/build/step3'/name;out.mkdir(parents=True,exist_ok=True)
 stage=src.replace(needle,needle+b'\n\n; VERIFY-only rendering ceiling: same-size matched control\n\tmove.w\t#$'+word.encode()+b',$6ac4a-$64a68(a1)')
 (out/'FerrariFormulaOne_WHD.s').write_bytes(stage)
 for local,target in [('SOURCES:Include',Path(os.environ['WHDLOAD'])/'Include'),('Sources:whdload',Path(os.environ['WHDLOAD'])/'Src/sources/whdload'),('lvo',r/'tmp/build/release/lvo')]:
  if not (out/local).exists():(out/local).symlink_to(target)
 cmd=[os.environ['VASM'],'-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+str(out),'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['NDK'],'-L','build.list','-o','FerrariFormulaOne.slave','FerrariFormulaOne_WHD.s']
 with (out/'build.log').open('w') as f:subprocess.run(cmd,cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
 print(name,word,hashlib.sha256((out/'FerrariFormulaOne.slave').read_bytes()).hexdigest())
a=(r/'tmp/build/step3/control/FerrariFormulaOne.slave').read_bytes();b=(r/'tmp/build/step3/no-road-lines/FerrariFormulaOne.slave').read_bytes();assert len(a)==len(b)
diff=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y];assert len(diff)<=2
(r/'manifest/step3-ceiling-build.json').write_text(json.dumps({'scope':'VERIFY-only SPS road edge-line routine omission; not playable','entry':hex(0x6ac4a),'original_word':original,'size':len(a),'different_file_bytes':diff},indent=2)+'\n')
