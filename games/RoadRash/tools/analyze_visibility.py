import sys,json,struct
from pathlib import Path
for tag in sys.argv[1:]:
 path=Path('tmp')/('visibility-'+tag)/'trace.json'
 if not path.exists():continue
 rows=json.loads(path.read_text());tracks={};events=[]
 for row in rows:
  b=bytes.fromhex(row['state']);cam=struct.unpack_from('>I',b,0x1e)[0];player=struct.unpack_from('>h',b,0x72)[0]
  for p in row['active'][1:]:
   if p==0xa5de0:continue
   o=p-0xa5d00;pos=struct.unpack_from('>I',b,o+4)[0];speed=struct.unpack_from('>h',b,o+0x12)[0];d=(pos>>16)-(cam>>16);gap=(pos-cam)/65536
   mode='front' if 0<=d<=30 else 'far' if d>30 else 'near-hidden' if player>=speed and d>-2 else 'mirror' if d>=-16 else 'rear-far'
   t=dict(field=row['field'],actor=hex(p),rider=b[o+0x71],cam=cam,pos=pos,gap=round(gap,5),segment_gap=d,player_speed=player,speed=speed,mode=mode,flags=b[o+0x68:o+0x74].hex())
   track=tracks.setdefault(p,[])
   if track and track[-1]['mode']!=mode and set([track[-1]['mode'],mode]) in [set(['front','far']),set(['mirror','near-hidden'])]:events.append([track[-1],t])
   track.append(t)
 print(tag,len(rows),'frames',rows[-1]['field'],'last field',len(events),'threshold transitions')
 for e in events[:24]: print(e)
 (path.parent/'threshold-transitions.json').write_text(json.dumps(events,indent=2))
