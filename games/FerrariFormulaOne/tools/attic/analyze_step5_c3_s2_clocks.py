from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];reports={}
for arm in ('native','candidate'):
 p=r/'tmp/step5'/('c3-s2-a500-'+arm);blocks=json.loads((p/'blocks.json').read_text());width=sum(x['bytes'] for x in blocks);offset=0
 for b in blocks:
  if b['name']=='clocks':break
  offset+=b['bytes']
 d=(p/'records.bin').read_bytes();n=len(d)//width;values=[]
 for i in range(n):
  v=d[i*width+offset:i*width+offset+20]
  values.append([sum(x*w for x,w in zip(v[j+3:j+10],(360000,36000,6000,600,100,10,1))) for j in (0,10)])
 assert n==100 and all(values[i][j]-values[i-1][j]==1 for i in range(1,n) for j in (0,1))
 reports[arm]=dict(records=n,calendar_tenths=values[-1][0]-values[0][0],session_tenths=values[-1][1]-values[0][1])
report=dict(status='passed',arms=reports)
(r/'manifest/step5-c3-s2-clock-replay.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
