#!/usr/bin/env python3
import json,sys
from pathlib import Path
from phase3_decode import decode
left,right=map(Path,sys.argv[1:3])
def read(p):
 m=json.loads((p/'metadata.json').read_text());return {int(f.stem):decode(f.read_bytes(),m) for f in (p/'state').glob('[0-9]*.bin')}
a,b=read(left),read(right);common=sorted(a.keys()&b.keys());x,y=a[max(a)],b[max(b)]
result={'left_fields':x['native_field'],'right_fields':y['native_field'],'left_lap_ticks':x['last_lap'],'right_lap_ticks':y['last_lap'],'max_distance_segments':max(abs(a[i]['distance_q8']-b[i]['distance_q8'])/256 for i in common),'max_lateral':max(abs(a[i]['lateral']-b[i]['lateral']) for i in common),'left_condition':x['condition'],'right_condition':y['condition'],'left_finish':x['finish'],'right_finish':y['finish'],'common_samples':len(common)}
result['pass']=bool(x['finish'] and y['finish'] and x['condition']==y['condition']==320 and abs(x['last_lap']-y['last_lap'])<=.01*x['last_lap'] and result['max_distance_segments']<=11.84 and result['max_lateral']<=280)
print(json.dumps(result,indent=2));(right/'lap-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['pass'], 'lap acceptance failed'
