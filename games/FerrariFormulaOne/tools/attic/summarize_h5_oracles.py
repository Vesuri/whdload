from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];rows=[]
for profile in ['a1200-fast','030-50','040-40','060-50']:
 pair=[]
 for arm in ['control','candidate']:
  p=r/f'tmp/step5/c4-q03-h5-oracle-{profile}-ccr-{arm}/result.json';j=json.loads(p.read_text());assert j['status']=='passed' and j['checked']==268 and j['oracle_error']==0 and j['warp_start']==j['warp_end']=='warp=0';assert j['benchmark_calls']==20000;assert j['mode']==int(arm=='candidate')
  if arm=='control':assert j['original_entry_control_verified'] and j['benchmark_entry'].startswith('4a79')
  else:assert j['benchmark_entry'].startswith('4ef9')
  pair.append(dict(arm=arm,result=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),slave_sha256=j['slave_sha256'],us_per_glyph=j['us_per_glyph'],resolution_us=j['resolution_us_per_glyph'],fields=j['field_end']-j['field_start']))
 assert pair[1]['us_per_glyph']+pair[1]['resolution_us']<pair[0]['us_per_glyph']-pair[0]['resolution_us']
 rows.append(dict(profile=profile,arms=pair,saving_percent=100*(1-pair[1]['us_per_glyph']/pair[0]['us_per_glyph'])))
report=dict(status='passed',cases_per_arm_profile=268,comparisons=rows,full_ccr_exact=True,whole_plane_pixels_exact=True,bytes_per_case=30960,benchmark_calls=20000,scope='Bounded 8x8 aligned live-font mono glyphs; eight different-colour outputs possible in three planes. Native fallback is retained for all larger/shifted/non-font/multicolour operations. No general size crossover or hardware CPU ranking inferred.',oracle_fixture='tmp/build/render-h5-oracle-ccr',warmup='After functional cases, control restores original entry, both flush caches and settle two VBLs after warp off; readback verifies entry and warp before benchmark.',case_description='256 selected cases: two live fonts, two source byte positions, all64 foreground/background pairs, destination byte positions and plane edges.12 native fallback cases: destination shifts1..7, widths7/9/16 and heights4/9.',measurement='VBL-field difference over20000 calls, ~1.002us/glyph endpoint resolution. Profile-specific empirical win for this class only.')
(r/'manifest/render-h5-oracles.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
