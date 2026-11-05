import json,subprocess,sys,hashlib
from pathlib import Path
from machine_profiles import PROFILES,banks
root=Path('tmp');prof=root/'prof';wait=[];off=[]
for prefix,expected,dst in [('s5-wait-v3',8,wait),('s5-wait-v3at',4,wait),('s5-wait-v3r',30,wait),('s5-final-off',21,off)]:
 rows=[]
 for p in root.glob(prefix+'-*-matrix.json'):rows.extend(json.loads(p.read_text()))
 assert len(rows)==expected,(prefix,len(rows));dst.extend(rows)
assert len({x['capture'] for x in wait+off})==63
trace_checks=0
for r in wait+off:
 p=prof/r['capture'];subprocess.run([sys.executable,'tools/check_render_patches.py',str(p)],check=True,stdout=subprocess.DEVNULL)
 m=json.loads((p/'metadata.json').read_text());code=(p/'game-code.bin').read_bytes();base=m['layout']['code_base']
 if (p/'render-costs.json').exists():
  memory=[(b,(p/('after-'+n+'.bin')).read_bytes()) for n,b,z in banks(m['configuration'])]
  after=next(d[base-b:base-b+len(code)] for b,d in memory if b<=base and base+len(code)<=b+len(d));assert after==code,r['capture'];trace_checks+=1
 assert (p/'cleanup.json').exists(),('not compacted',r['capture'])
selected={p:6 if p in ['a500','a500-fast','a1200-020'] else 0 if p=='a1200-030-50' else 2 for p in PROFILES};matrix=[]
for profile in PROFILES:
 for w in ['A','B','attract']:
  a=next(x for x in off if x['capture']==f's5-final-off-{profile}-{w.lower()}-0')
  b=a if selected[profile]==0 else next(x for x in wait if x['capture'].endswith(f'-{profile}-{w.lower()}-{selected[profile]}'))
  ma,mb=[json.loads((prof/x['capture']/'metadata.json').read_text()) for x in [a,b]]
  assert ma['slave_sha256']==mb['slave_sha256'];assert ma['game_sha256']==mb['game_sha256'];assert ma['emulator_sha256']==mb['emulator_sha256']
  ca,cb=[dict(m['configuration']) for m in [ma,mb]];ca.pop('WHD_ARGS');cb.pop('WHD_ARGS');assert ca==cb
  matrix.append(dict(profile=profile,window=w,selected_custom3=selected[profile],off=a,on=b,unchanged=selected[profile]==0,delta_swaps=b['swaps']-a['swaps'],fps_gain_percent=100*(b['swaps']/a['swaps']-1)))
report=dict(passed=True,wait_experiment_runs=42,final_disabled_runs=21,patch_audits=63,sites_per_audit=13,trace_code_unchanged=trace_checks,selection=selected,matrix=matrix,scope='500 PAL fields per window. Identical retained binaries per fixture and same simulation in both arms. Original renderer retained on 030, so its selected column is the disabled run, not a duplicate trial. Whole-window results, not equal-scene or net-original performance proof.')
(root/'s5-final-report.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='matrix'})
for profile in PROFILES:print(profile,[(r['window'],r['off']['swaps'],r['on']['swaps']) for r in matrix if r['profile']==profile])
