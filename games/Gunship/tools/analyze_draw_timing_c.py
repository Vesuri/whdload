"""Frame age/cadence from compiled draw probe; completion is not scanout."""
from pathlib import Path
import struct,json,statistics,sys
for directory in sys.argv[1:]:
 p=Path(directory);b=(p/'draw-frames.bin').read_bytes();assert b[:8]==b'GSSCAN01';count=int.from_bytes(b[8:12],'big');rows=[]
 for i in range(max(0,count-512),count):
  x=b[16+i%512*56:16+(i%512+1)*56];f,w,start,end=struct.unpack_from('>4I',x)
  if 20<=w<80:
   assert end>=start>=f
   rows.append(dict(index=i,field=f,world=w,start=start,end=end,lag=start-f,draw=end-start,age=end-f,camera=list(struct.unpack_from('>6H',x,16))))
 assert len(rows)>1
 rate_rows=json.loads((p/'actual-rate.json').read_text())['rows']
 rates={r['rate'] for r in rate_rows};assert len(rates)==1 and rates<={50,60}
 rate=rates.pop()
 span=rows[-1]['end']-rows[0]['end']
 r=dict(rate=rate,completion_fps=(len(rows)-1)*rate/span,total_frames=count,window_frames=len(rows),same_world_pairs=sum(a['world']==b['world'] for a,b in zip(rows,rows[1:])),same_world_camera_changes=sum(a['world']==b['world'] and a['camera']!=b['camera'] for a,b in zip(rows,rows[1:])),worlds_between_frames=[b['world']-a['world'] for a,b in zip(rows,rows[1:])],duration_fields=span,stats={k:dict(min=min(r[k] for r in rows),max=max(r[k] for r in rows),median=statistics.median(r[k] for r in rows)) for k in ['lag','draw','age']},rows=rows,scope='Controlled workload: native draw completion, not display scanout or input latency. Age measured from last consumed field.')
 (p/'draw-timing.json').write_text(json.dumps(r,indent=2)+'\n');print(directory,{k:v for k,v in r.items() if k not in ['rows','scope','worlds_between_frames']})
