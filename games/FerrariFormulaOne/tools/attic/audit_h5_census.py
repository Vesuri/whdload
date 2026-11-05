from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/audit_render_profile.py').read_text().replace('rc2-trace','h5-candidate').replace('rc2-census','h5-census')
exec(compile(s,str(r/'tools/audit_render_profile.py'),'exec'))
