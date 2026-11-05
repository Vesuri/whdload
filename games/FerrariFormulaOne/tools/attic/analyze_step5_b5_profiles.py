from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks'];report={'profiles':{},'scope':'Matched loop-125 start, 20 complete lean updates after excluding the first installation interval. Only unsuccessful pacing polls excluded. Owner/per-car/classify totals must agree exactly. Helper gate is mean car0 conv_helper segment <= 5000 cycles on 020+Fast.'}
for profile in ('a1200-fast','a1200'):
 paths=[r/f'tmp/step5/{profile}-b5-v5-matched-{suffix}' for suffix in ('b4','b5')];data=[]
 for p,build in zip(paths,('step5-b4-v4','step5-b5-v5')):
  result=json.loads((p/'result.json').read_text());assert result['status']=='complete' and result['slave_sha256']==hashlib.sha256((r/f'tmp/build/{build}/lean/fine.slave').read_bytes()).hexdigest()
  owner=json.loads((p/'profile.json').read_text());car=json.loads((p/'percar.json').read_text());cls=json.loads((p/'classified.json').read_text())
  values=car['per_update_totals'];assert len(values)==20 and values==cls['per_update_totals'];assert abs(sum(values)/20-owner['mean_cycles'])<0.01
  five=[sum(values[i:i+5])/5 for i in range(16)]
  data.append(dict(mean_cycles=owner['mean_cycles'],player_cycles=car['segment_totals_exact']['car0'],helper_cycles=car['segment_categories_exact']['car0']['conv_helper'],peak_cycles=max(values),worst_rolling_five=max(five),capture=str(p.relative_to(r)),slave_sha256=result['slave_sha256']))
 before,after=data;states=[(p/'start.bin').read_bytes() for p in paths];mismatch=[]
 for b in blocks:
  a=int(b['address'],16);n=b['bytes']
  if states[0][a:a+n]!=states[1][a:a+n]:mismatch.append(b['name'])
 assert not mismatch
 report['profiles'][profile]=dict(before=before,after=after,exact_start=True,player_reduction_percent=100*(1-after['player_cycles']/before['player_cycles']),total_reduction_percent=100*(1-after['mean_cycles']/before['mean_cycles']),player_gate_passed=after['helper_cycles']<=5000 if profile=='a1200-fast' else None)
 print(profile,report['profiles'][profile])
report['status']='passed' if report['profiles']['a1200-fast']['player_gate_passed'] else 'failed';(r/'manifest/step5-b5-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['status']=='passed'
