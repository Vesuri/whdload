from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/audit_step5_c1_profile.py').read_text()
old='max(sum(cycles[i:i+5])/5 for i in range(len(cycles)-4))'
assert old in s
s=s.replace(old,'(max(sum(cycles[i:i+5])/5 for i in range(len(cycles)-4)) if len(cycles)>=5 else None)')
exec(compile(s,str(r/'tools/audit_step5_c1_profile.py'),'exec'))
