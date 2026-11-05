from pathlib import Path
import os,sys
r=Path(__file__).resolve().parents[1];p=r.parents[1]/'Games/FerrariFormulaOne/build.py';s=p.read_text().replace("flags0=['FF1_PRODUCTION=1'","flags0=['FF1_PATCH_LEDGER_BYTES=0','FF1_PRODUCTION=1'")
sys.argv=[str(p),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(r/'tmp/build/production-fault')]
exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
s=(r/'tools/test_production_smoke.py').read_text().replace("kind='production-smoke'","kind='production-fault'").replace("tmp/build/production/FerrariFormulaOne.slave","tmp/build/production-fault/FerrariFormulaOne.slave")
a=s.index(" cmd('delete')\n faults=");z=s.index('\nfinally:',a)
s=s[:a]+''' cmd('delete');target=host+hs['FF1PerformanceAbort'];cmd(f'break *{target}');assert 'Breakpoint' in cmd('continue')
 report['stop_pc']=hex(val('$pc'));assert val('$pc')==target
 report['status']='passed';report['expected_failure']='zero-sized patch ledger exits through WHDLoad error instead of a diagnostic spin or silent loop fallback'
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\\n');print(report,flush=True)
'''+s[z:]
(r/'tools/test_production_fault.py').write_text(s)
