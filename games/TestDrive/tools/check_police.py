#!/usr/bin/env python3
"""Bounded phase-8 pursuit/event checks from consecutive VBL samples."""
import argparse,json
from pathlib import Path

def check(folder):
 meta=json.loads((folder/'capture.json').read_text())
 s=json.loads((folder/'states/samples.json').read_text())
 p=s[0]['period'];assert p in (2,5)
 assert len(s)==meta['fields'] and all(b['vbl']==a['vbl']+1 for a,b in zip(s,s[1:]))
 assert all(x['period']==p for x in s)
 # Observe an entire ticket counter, including departure and slot culling.
 stops=[(i,x['police_stop']) for i,x in enumerate(s) if i and x['police_stop']!=s[i-1]['police_stop']]
 assert [v for _,v in stops]==list(range(1,31))+[0],('incomplete/repeated stop',stops)
 intervals=[b[0]-a[0] for a,b in zip(stops[:29],stops[1:30])]
 assert set(intervals)<=({4,6} if p==2 else {5}),('wrong stop cadence',intervals)
 increments=[i for i,x in enumerate(s) if i and x['police_clock']==s[i-1]['police_clock']+1 and s[i-1]['police_clock']>1]
 clock_intervals=[b-a for a,b in zip(increments,increments[1:])]
 assert len(clock_intervals)>80 and set(clock_intervals)<=({4,6} if p==2 else {5})
 first,last=stops[0][0],stops[-1][0]
 assert all(x['speed']==0 for x in s[first:last]),'vehicle moved during ticket stop'
 crashed=bool(meta['options']['C5']&2)
 jumps=[(i,b['samples']-a['samples']) for i,(a,b) in enumerate(zip(s,s[1:]),1) if b['samples']-a['samples']>2]
 event={}
 if crashed:
  assert [v for _,v in jumps]==[240],('crash penalty',jumps)
  entries=[i for i,x in enumerate(s) if i and x['event']==1 and s[i-1]['event']==0]
  recoveries=[i for i,x in enumerate(s) if i and x['event']==0 and s[i-1]['event']==1]
  assert len(entries)==len(recoveries)==1
  assert s[0]['chances']==5 and s[-1]['chances']==4
  penalty=jumps[0][0];recovery=recoveries[0]
  assert len({x['samples'] for x in s[penalty:recovery]})==1,'clock ran during original blocking event'
  event=dict(entry=entries[0],penalty=penalty,recovery=recovery)
 else:
  assert not jumps and all(x['event']==0 and x['chances']==5 for x in s)
  assert s[last-1]['samples']>s[first]['samples'],'clock froze during police stop'
 return dict(status='PASS',period=p,stop_entry=first,release=last,stop_intervals=sorted(set(intervals)),
             clock_intervals=sorted(set(clock_intervals)),count_during_stop=s[last-1]['samples']-s[first]['samples'],crash=event,
             scope=('One forced pursuit' if meta['options']['C5']&4 else 'One natural pursuit')+'; event animation timing retained, not normalized')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('captures',nargs='+',type=Path);a=p.parse_args()
 print(json.dumps({str(x):check(x) for x in a.captures},indent=2))
