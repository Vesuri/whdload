from pathlib import Path
import json,hashlib,statistics
r=Path(__file__).resolve().parents[1];base=r/'tmp/step5'
paths=[base/('c4-q03-release-census-a1200-fast-calibration-'+x+'-v2') for x in ('default','explicit')]
results=[json.loads((p/'result.json').read_text()) for p in paths]
windows=[[json.loads(l) for l in (p/'window.jsonl').read_text().splitlines()] for p in paths]
for result,rows in zip(results,windows):
 assert result['status']=='passed' and result['error']==0
 assert result['survey_meta']['cpucycleunit']==128 and result['survey_meta']['cpu_model']==68020
 assert len(rows)==1001 and [x['field'] for x in rows[1:]]==list(range(1000))
 assert result['end_context'][0]-result['start_context'][0]==1000
 assert all(x['cycles']==284204 for x in rows[1:])
 assert abs(statistics.mean(x['cycles'] for x in rows[1:])*rows[0]['vblank_hz']/1e6-14.18758)<0.000001
assert windows[0][1:]==windows[1][1:]
assert results[0]['start_context']==results[1]['start_context'] and results[0]['end_context']==results[1]['end_context']
report={'status':'passed','scope':'Explicit 14.18758 MHz equals stock 020 multiplier: all 1000 complete DMA rows, CPU cycle totals, and driving contexts exactly match. No debugger memory writes.','cpu_unit':128,'cycles_per_field':284204,'effective_mhz':14.18758,'emulator_sha256':results[0]['emulator_sha256'],'paths':[str(p.relative_to(r)) for p in paths],'patch_sha256':hashlib.sha256((r/'tools/release-clock-overflow.patch').read_bytes()).hexdigest(),'rejected_variants':['candidate: overflowing and wrong clock scale','clock-fixed: widened multiplication, still eight times too slow'],'frequency_rule':'floor(512 * (baseclock/8) / requested_hz); report actual quantized CPU budget from cycles per field.'}
(r/'manifest/release-clock-calibration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
