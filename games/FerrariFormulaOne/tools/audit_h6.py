from pathlib import Path
import json,hashlib,collections,subprocess
r=Path(__file__).resolve().parents[1];p=r/'tmp/manifest/render-h6-baseline.json';data=json.loads(p.read_text());assert data['status']=='passed' and len(data['results'])==28
for key,row in data['results'].items():
 result=r/row['result'];d=json.loads(result.read_text());assert len(d['interval_fields'])==300 and d['error']==0 and d.get('heavy_incomplete',0)==0
 assert d['emulator_sha256']=='e411569ca9e0c30b0cb62b831c88a6dcab4f415517cfcf43fb290d1d5d57171c'
 assert d['mean_ms']==sum(d['interval_fields'])/300*71051/3546895*1000
 census=[json.loads(x) for x in (result.parent/'window.jsonl').read_text().splitlines()];slots=sum(x['dma'][5] for x in census[1:])
 if '-bce/' in key:assert slots>0
 elif not key.startswith('a1200-fast/'):assert slots==0
 row['observed_blitter_dma_slots']=slots;row['result_sha256']=hashlib.sha256(result.read_bytes()).hexdigest();row['census_metadata']=census[0]
data.update(base_commit='914e24b',code_commit='25ca4b9',source_build_sha256='57900954b6eb18f1691f3ff8f9b51bcb4beb8a6c3456b6d33f1268cc810c9316',target='Every one of 300 complete intervals is exactly two PAL fields: mean=p95=40.063774089732 ms,24.960204641736215 FPS.',launch='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache; startup warp, measurement warp off.',initial_launch_rejected='CUSTOM1=1 normal020 demo left racing before300 intervals; not an accepted baseline. Repeated entire matrix under established H-series CUSTOM1=0 options.')
p.write_text(json.dumps(data,indent=2)+'\n');print('H6 verified:28 runs,300 complete intervals each,actual blitter DMA model checked')
