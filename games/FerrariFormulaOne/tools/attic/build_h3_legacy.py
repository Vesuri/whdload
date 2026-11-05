from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_b8_default_control.py').read_text().replace('step5-b8-default-control','render-h3-default-control').replace("'tmp/build/step5-b8-v3/lean/fine.slave'","'tmp/build/render-h3/FerrariFormulaOne.slave'").replace("'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave'","'tmp/build/render-h3/host.slave'").replace("'tmp/build/step5-b7-loader-v3/build.list'","'tmp/build/render-h3/host.list'").replace("'b8'","'production'")
exec(compile(s,str(r/'tools/build_step5_b8_default_control.py'),'exec'))
s=(r/'tools/test_release_default_c1.py').read_text().replace('release-default-c1-control','render-h3-default-c1-control').replace('production-default-control','render-h3-default-control').replace('release-default-c','render-h3-default-c')
(r/'tools/test_h3_legacy.py').write_text(s)
s=(r/'tools/build_release_default_c1.py').read_text().replace('release-default-c1-control','render-h3-default-c1-control').replace('production-default-control','render-h3-default-control');s=s[:s.index("p=r/'tools/test_release_default_c1.py'")];exec(compile(s,str(r/'tools/build_release_default_c1.py'),'exec'))
