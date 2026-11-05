from pathlib import Path
from functools import lru_cache
import json,re,struct,sys
l=Path('tmp/build/collision.slave.lst').read_text(encoding='latin1')
@lru_cache(None)
def s(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
def capture(folder,w):
 p=folder/f'world-{w}';a=(p/'arena.bin').read_bytes();h=(p/'h0.bin').read_bytes()
 return dict(world=w,field=int.from_bytes(a[s('RT_CLOCK')+4:s('RT_CLOCK')+8],'big'),kind=h[0xc6db],life=h[0xc6d5],frame=h[0xc6e1],timer=h[0xc729],mask=int.from_bytes(h[0xba08:0xba0a],'big'),safe=int.from_bytes(a[s('RT_ACTOR_PRESENT')+s('AC_SAFE'):s('RT_ACTOR_PRESENT')+s('AC_SAFE')+2],'big'),generation=int.from_bytes(a[s('RT_ACTOR_GENERATIONS')+20:s('RT_ACTOR_GENERATIONS')+24],'big'))
for name in sys.argv[1:]:
 p=Path(name);worlds=sorted(int(d.name.split('-')[1]) for d in p.glob('world-*') if d.is_dir())
 allrows=[capture(p,w) for w in worlds]
 start=next(i for i,r in enumerate(allrows) if r['kind']==9)
 end=next(i for i in range(start+1,len(allrows)) if allrows[i]['kind']==0)
 rows=allrows[start:end+1]
 assert (rows[0]['kind'],rows[0]['life'],rows[0]['frame'],rows[0]['timer'])==(9,64,0,12)
 timer=12;frame=0;life=64;field=rows[0]['field'];finished=None
 for row in rows[1:]:
  while field<row['field']:
   field+=1;timer=(timer-1)&255
   if timer&128:timer=8;frame+=1
   if frame>=6:
    frame=6;life=1
    if finished is None:finished=field
  life=(life-1)&255
  assert (row['life'],row['frame'],row['timer'])==(life,frame,timer),row
  assert row['kind']==(9 if life else 0)
 for row in rows:
  assert row['generation']==1 and not(row['safe']&32)
  assert bool(row['mask']&32)==bool(row['life'])
 r=dict(rows=rows,animation_finished_field=finished,release_field=rows[-1]['field'],release_delay_fields=rows[-1]['field']-rows[0]['field'],scope='Controlled type-8 impact to type-9 effect, native field animation and world release; unchanged allocation generation.')
 (p/'effect-timing-comparison.json').write_text(json.dumps(r,indent=2)+'\n')
 print(p.name,'animation complete',finished,'released',rows[-1]['field'],'delay',r['release_delay_fields'])
