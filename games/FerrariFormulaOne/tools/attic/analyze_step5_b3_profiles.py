from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks'];report={'scope':'Matched pre-activation loop 125 state. First complete loop (installation) excluded; next 20 quanta compared, four complete native pulse periods. All-car S3 and Plan B necessarily diverge after activation. Lean builds, with repeated pacing polls excluded but final due check retained.','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/f'tmp/step5/{profile}-b3-v4-matched-{v}' for v in ('s3','b3')]
 if not all((p/'profile.json').exists() for p in paths):continue
 data=[(p/'start.bin').read_bytes() for p in paths];mismatch=[]
 for x in blocks:
  a=int(x['address'],16);n=x['bytes']
  if data[0][a:a+n]!=data[1][a:a+n]:mismatch.append(x['name'])
 rows=[json.loads((p/'profile.json').read_text()) for p in paths];exact=[]
 for p,row in zip(paths,rows):
  per=json.loads((p/'percar.json').read_text());cl=json.loads((p/'classified.json').read_text())
  exact.append(row['per_update_cycles']==per['per_update_totals']==cl['per_update_totals'])
 b3=rows[1]['per_update_cycles'];means=[sum(b3[i:i+5])/5 for i in range(0,len(b3),5)];rolling=[sum(b3[i:i+5])/5 for i in range(len(b3)-4)]
 row=dict(start_exact=not mismatch,start_mismatches=mismatch,analyser_totals_exact=exact,complete_updates=[d['complete_updates'] for d in rows],s3_cycles=rows[0]['mean_cycles'],b3_cycles=rows[1]['mean_cycles'],five_quantum_means=means,worst_rolling_five=max(rolling),peak=max(b3),saving_percent=100*(1-rows[1]['mean_cycles']/rows[0]['mean_cycles']))
 row['passed']=not mismatch and all(exact) and row['complete_updates']==[20,20] and (profile!='a1200-fast' or max(rolling)<=200000 and max(b3)<=400000)
 report['profiles'][profile]=row;print(profile,row)
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-b3-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n')
