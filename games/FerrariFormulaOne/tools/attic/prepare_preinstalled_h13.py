from pathlib import Path
import hashlib,json,subprocess,shutil
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=r/'tmp/release/FerrariFormulaOne-1.02-h13';c.mkdir(exist_ok=True)
b=r/'tmp/build/preinstalled-h13/FerrariFormulaOne.slave'
assert b.read_bytes()==(r/'tmp/build/render-h13/FerrariFormulaOne.slave').read_bytes()
v=json.loads((r/'manifest/render-h13-validation.json').read_text());assert v['status']=='passed'
shutil.copy2(b,c/b.name)
for n in ['Launch-Performance','Launch-Legacy']:shutil.copy2(r/'tmp/release/FerrariFormulaOne-1.02-rc2'/n,c/n)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
files=subprocess.check_output(['git','ls-files','Games/FerrariFormulaOne*'],cwd=repo,text=True).splitlines()
info={'candidate':'FerrariFormulaOne-1.02-h13','source_revision':head,'slave_bytes':b.stat().st_size,'slave_sha256':sha(b),'source_hashes':{n:sha(repo/n) for n in files if (repo/n).is_file()},'scope':'Local development snapshot through H13. Reduced representative emulator acceptance; not a new complete release qualification.','human_playtesting':'deferred','real_hardware':'deferred','h12':'dropped','b8_pal':'Inherited border-colour diagnostic pulse remains; cleanup separate.'}
(c/'BuildInfo.json').write_text(json.dumps(info,indent=2)+'\n')
intro='''# H13 development snapshot\n\nThis package includes the accepted rendering changes through H13 and RC2's\ndriving-control correction. H1 and H12 are excluded. H13 passes the reduced\nrepresentative correctness/performance checks below. The complete historical\nrelease matrix has not been rerun for this snapshot. Human full-race playtesting\nand real hardware remain deferred. The B8-PAL diagnostic border pulse remains.\n\n'''
plan=(repo/'Games/FerrariFormulaOne/RENDERING_PLAN.md').read_text()
h13=plan[plan.index('## H13 — Bounded CPU gauge strips'):]
(c/'RELEASE_QUALIFICATION.md').write_text(intro+h13+'\n\n# RC2 driving-control correction\n\n'+(repo/'Games/FerrariFormulaOne/README.md').read_text()+'\n\n# Historical qualification (scope and corrections retained)\n\n'+(repo/'Games/FerrariFormulaOne/RELEASE_QUALIFICATION.md').read_text())
print(head,sha(b))
