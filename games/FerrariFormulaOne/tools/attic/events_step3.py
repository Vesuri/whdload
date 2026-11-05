#!/usr/bin/env python3
from pathlib import Path
import sys,json,statistics,struct
r=Path(__file__).resolve().parents[1]
def analyze(name):
 p=r/'tmp/step3'/name;rows=[json.loads(l) for l in (p/'window.jsonl').read_text().splitlines()];meta=rows.pop(0)
 b=(p/'anchor.bin').read_bytes();timing=struct.unpack_from('>I',b,0x6a306)[0] if b[0x6a304:0x6a306]==b'\x4e\xb9' else None
 pairs={'car_update':(0x67120,0x65606),'prior_blitter_barrier':(0x654e6,0x654ec),'display_request':(0x654f6,0x654fc),'beam_wait':(0x65728,0x65734),'road_geometry_and_drawing':(0x6578a,0x65790),'main_loop':(0x65174,0x65174)}
 if timing:pairs['existing_two_WaitTOF']=(timing,0x6a30a)
 active={};spans={k:[] for k in pairs};ranges={k:[] for k in pairs};clock=0
 blit_returns={v+6 for v in json.loads((r/'manifest/step3-blitter-calls.json').read_text())};blit_start=None;blit_spans=[];blit_ranges=[]
 for row in rows:
  for pc,offset,sp in row.get('events',[]):
   if sp>>12!=0x18:continue
   now=clock+offset
   if pc==0x2a130:blit_start=now
   elif pc in blit_returns and blit_start is not None:blit_spans.append(now-blit_start);blit_ranges.append((blit_start,now));blit_start=None
   for key,(start,end) in pairs.items():
    if pc==end and key in active:
     begin=active.pop(key);spans[key].append(now-begin);ranges[key].append((begin,now))
    if pc==start and key not in active:active[key]=now
  clock+=row['cycles']
 spans['all_WaitBlit_wrappers']=blit_spans
 units_per_second=statistics.mean(row['cycles'] for row in rows)*meta['vblank_hz']
 result={k:{'completed_calls':len(v),'mean_ms':statistics.mean(v)*1000/units_per_second if v else None,'max_ms':max(v)*1000/units_per_second if v else None,'mean_trace_units':statistics.mean(v) if v else None,'total_ms':sum(v)*1000/units_per_second,'elapsed_share_percent':100*sum(v)/clock} for k,v in spans.items()}
 waits=blit_ranges+ranges['beam_wait']+ranges.get('existing_two_WaitTOF',[])
 work=[]
 for begin,end in ranges['main_loop']:
  clipped=sorted((max(begin,a),min(end,b)) for a,b in waits if b>begin and a<end)
  merged=[]
  for a,b in clipped:
   if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
   else:merged.append((a,b))
  work.append(end-begin-sum(b-a for a,b in merged))
 result['complete_loop_work_excluding_observed_sync']={'completed_calls':len(work),'mean_ms':statistics.mean(work)*1000/units_per_second if work else None,'p95_ms':sorted(work)[int((len(work)-1)*.95+.5)]*1000/units_per_second if work else None,'max_ms':max(work)*1000/units_per_second if work else None,'note':'Elapsed main-loop time minus union of recorded WaitTOF, beam wait and WaitBlit spans. Includes IRQ and other unbracketed stalls.'}
 (p/'phases.json').write_text(json.dumps({'scope':'Elapsed inclusive spans; IRQ/OS time within each span is included. Partial boundary calls excluded. Nested spans must not be added.','phases':result},indent=2)+'\n');print(name,result)
if __name__=='__main__':
 for name in sys.argv[1:]:analyze(name)
