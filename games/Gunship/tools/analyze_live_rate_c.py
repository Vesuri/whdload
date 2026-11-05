"""Summarize nominal PAL/NTSC live rate without claiming display latency."""
from pathlib import Path
import json,sys
for arg in sys.argv[1:]:
 folder=Path(arg);rows=json.loads((folder/'result.json').read_text())['rows'];first,last=rows[0],rows[-1];rate=first['rate']
 assert rate in (50,60)
 for r in rows:
  assert r['rate']==rate and r['flight']==0 and r['setup']==0 and r['ready']==1 and r['owner']==1,r
  assert r['scheduler_fault']==0 and r['history_lost']==0,r
  assert 0<=r['clock_ticks']-r['worlds']<=1,r
 elapsed=(last['published_field']-first['published_field'])/rate
 backlogs=[r['published_field']-r['last_field'] for r in rows]
 discarded=last['history_discarded']-first['history_discarded']
 if not last['history_discarded']:
  for r in rows:assert r['clock_fields']*3==r['clock_ticks']*rate+r['phase'],r
 result=dict(machine=folder.name,nominal_field_rate=rate,observations=len(rows),elapsed_seconds=elapsed,
  completed_worlds=last['worlds']-first['worlds'],worlds_per_second=(last['worlds']-first['worlds'])/elapsed,
  consumed_fields=last['steps']-first['steps'],backlog_first=backlogs[0],backlog_last=backlogs[-1],backlog_min=min(backlogs),backlog_max=max(backlogs),
  lost=last['history_lost'],discarded_in_window=discarded,discarded_total=last['history_discarded'],
  tick_count_endpoint_bound_hz=1/elapsed,completion_in_progress_bound_hz=1/elapsed,
  display_latency_measured=False)
 (folder/'rate-summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
