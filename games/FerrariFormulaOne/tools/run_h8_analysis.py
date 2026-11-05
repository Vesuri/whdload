from pathlib import Path
import json,gzip,hashlib,subprocess,sys,shutil
r=Path(__file__).resolve().parents[1]
index=json.loads((r/'tmp/manifest/render-h7-traces.json').read_text());out={}
for name,item in index.items():
 p=r/item['trace'];raw=p/'detail.bin'
 assert not raw.exists()
 with gzip.open(p/'detail.bin.gz','rb') as src,raw.open('wb') as dst:shutil.copyfileobj(src,dst)
 try:
  assert hashlib.file_digest(raw.open('rb'),'sha256').hexdigest()==item['raw_sha256']
  result=json.loads((p/'result.json').read_text())
  assert hashlib.file_digest(Path(result['slave']).open('rb'),'sha256').hexdigest()==result['slave_sha256']
  assert '--uae_blitter_cycle_exact=true' in result['extra_args']
  with (p/'h8-calls.log').open('w') as log:subprocess.run([sys.executable,str(r/'tools/analyze_h8_calls.py'),str(p)],stdout=log,stderr=subprocess.STDOUT,check=True)
  a=json.loads((p/'hi25-analysis.json').read_text());c=json.loads((p/'h8-calls.json').read_text())
  assert abs(sum(x['total'] for x in c['calls'].values())-a['mean_draw_ms'])<0.02
  out[name]={'trace':item,'slave_sha256':result['slave_sha256'],'post_wait_ms':a['mean_after_wait_ms'],'stages':a['stage_ms_per_draw'],'categories':a['draw_category_ms_per_draw'],'calls':c,'dma_share':a['dma_slot_share']}
  print(name,a['mean_after_wait_ms'],flush=True)
 finally:raw.unlink()
(r/'tmp/manifest/render-h8-analysis.json').write_text(json.dumps({'status':'passed','source_commit':'975daceb65ca7d088079cd4424ddca4b71e641b7','scope':'Reanalysis of accepted H7 30-field cycle-exact grid traces; no new emulator runs or game changes','profiles':out},indent=2)+'\n')
