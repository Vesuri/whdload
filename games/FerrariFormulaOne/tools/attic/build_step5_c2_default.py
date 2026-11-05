from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_b8_default_control.py').read_text().replace('step5-b8-default-control','step5-c2-default-control').replace("'tmp/build/step5-b8-v3/lean/fine.slave'","'tmp/build/step5-c2/020/candidate.slave'").replace("'b8'","'c2'")
# Both coarse builds are same length. Their entry wrapper is 68000-safe; only
# selected, disabled coarse code has CPU-specific flag saves. Use 020 bytes
# for both default-off tests, which cannot execute those entries.
exec(compile(s,str(r/'tools/build_step5_b8_default_control.py'),'exec'))
s=(r/'tools/test_step5_b8_default.py').read_text().replace('b8','c2')
(r/'tools/test_step5_c2_default.py').write_text(s)
