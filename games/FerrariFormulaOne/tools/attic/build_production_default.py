from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_b8_default_control.py').read_text().replace('step5-b8-default-control','production-default-control').replace("'tmp/build/step5-b8-v3/lean/fine.slave'","'tmp/build/production/FerrariFormulaOne.slave'").replace("'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave'","'tmp/build/production/host.slave'").replace("'tmp/build/step5-b7-loader-v3/build.list'","'tmp/build/production/host.list'").replace("'b8'","'production'")
exec(compile(s,str(r/'tools/build_step5_b8_default_control.py'),'exec'))
s=(r/'tools/test_step5_b8_default.py').read_text().replace('b8','production')
(r/'tools/test_production_default.py').write_text(s)
