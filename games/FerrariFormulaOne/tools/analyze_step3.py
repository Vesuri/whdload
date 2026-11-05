#!/usr/bin/env python3
from pathlib import Path
import json,sys,collections,statistics,hashlib
root=Path(__file__).resolve().parents[1]
def analyze(p):
 with (p/'window.jsonl').open() as f:
  meta=json.loads(next(f));rows=[json.loads(l) for l in f]
 assert [row['field'] for row in rows]==list(range(len(rows))), 'missing or reordered field'
 hz=meta['vblank_hz'];changes=[r['field'] for prev,r in zip(rows,rows[1:]) if prev['planes']!=r['planes']]
 assert all(all(r['planes']) for r in rows),'missing bitplane DMA'
 intervals=[b-a for a,b in zip(changes,changes[1:])]
 def quantile(v,q):return sorted(v)[min(len(v)-1,int((len(v)-1)*q+0.5))] if v else None
 pcs=collections.defaultdict(lambda:[0,0]);dma=collections.Counter();wholecycles=0;recorded=0
 for r in rows[:500]:
  wholecycles+=r['cycles'];recorded+=r['recorded_cycles']
  for pc,c,n in r['pcs']:pcs[pc][0]+=c;pcs[pc][1]+=n
  dma.update(dict(enumerate(r['dma'])))
 counts={hex(a):sum(n for r in rows for pc,c,n in r['pcs'] if pc==a) for a in (0x65606,0x654ec,0x654fc,0x6a304,0x67120)}
 if not recorded:counts={k:None for k in counts}
 result={'name':p.name,'fields':len(rows),'meta':meta,'bank_changes':changes,'presented_fps_count':len(changes)*hz/len(rows),'complete_interval_fps':hz/statistics.mean(intervals) if intervals else None,'interval_fields':{'mean':statistics.mean(intervals) if intervals else None,'p50':quantile(intervals,.5),'p95':quantile(intervals,.95),'p99':quantile(intervals,.99),'max':max(intervals) if intervals else None},'cycle_values':dict(collections.Counter(r['cycles'] for r in rows)),'recorded_cycle_fraction':recorded/wholecycles if wholecycles and recorded else None,'pc_landmark_counts':counts,'dma_slots_first500':dict(dma),'top_pcs_first500':[{'pc':hex(pc),'cycles':v[0],'hits':v[1],'share':v[0]/wholecycles} for pc,v in sorted(pcs.items(),key=lambda x:-x[1][0])[:60]],'all_pcs_first500':{hex(k):v for k,v in pcs.items()},'window_sha256':hashlib.sha256((p/'window.jsonl').read_bytes()).hexdigest()}
 (p/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
 print(p.name,'FPS',round(result['presented_fps_count'],3),'intervals',result['interval_fields'],'accounting',result['recorded_cycle_fraction'],'landmarks',counts)
 return result
if __name__=='__main__':
 for n in sys.argv[1:]:analyze(root/'tmp/step3'/n)
