from pathlib import Path
import json,statistics,hashlib
from analyze_step3 import analyze
r=Path(__file__).resolve().parents[1];base=r/'tmp/step5';report={'status':'passed','scope':'Enabled production: two fresh 1000-field DMA windows and 60 simulated seconds plus 300 presentations per accelerated profile. No hardware-rate claim; baselines/cache/MMU/state qualification separate.','profiles':{}}
cal=json.loads((r/'manifest/release-clock-calibration.json').read_text());assert cal['status']=='passed'
for profile in ('030-50','040-25','040-40','060-50'):
 pair=[base/f'c4-q03-release-census-{profile}-clock-v2-{x}' for x in ('a','b')]
 results=[json.loads((p/'result.json').read_text()) for p in pair]
 windows=[[json.loads(l) for l in (p/'window.jsonl').read_text().splitlines()] for p in pair]
 for result,rows in zip(results,windows):
  assert result['status']=='passed' and result['error']==0 and result['selection']==2
  assert result['emulator_sha256']==cal['emulator_sha256'] and result['slave_sha256']=='60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836'
  assert result['end_context'][0]-result['start_context'][0]==1000 and len(rows)==1001
  meta=rows[0];assert meta['cpucycleunit']==512*(meta['baseclock']//8)//meta['cpu_frequency']
  expected=512*71051/meta['cpucycleunit'];assert all(abs(x['cycles']-expected)<=1 for x in rows[1:])
 assert windows[0]==windows[1],profile+' repeats differ'
 a=analyze(pair[0]);analyze(pair[1]);assert a['presented_fps_count']>=5.54
 timing=json.loads((base/f'c4-q03-release-timing-{profile}-clock-v2/result.json').read_text())
 assert timing['status']=='passed' and timing['error']==0 and timing['simulated_seconds']==60 and timing['error_percent']<=1
 assert timing['emulator_sha256']==cal['emulator_sha256']
 report['profiles'][profile]={'dma_fps':a['presented_fps_count'],'frame_fields':a['interval_fields'],'fps_300':timing['fps'],'elapsed_for_60s':timing['elapsed_seconds'],'error_percent':timing['error_percent'],'configuration':windows[0][0],'effective_mhz':results[0]['effective_mhz'],'repeat_exact':True,'dma_window_sha256':a['window_sha256'],'instruction_costs':'unavailable from DMA-only census'}
(r/'manifest/release-accelerated-enabled.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
