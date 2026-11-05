"""Validate the isolated, native Monza qualifying-to-race boundary reproduction."""
import json,re,struct,hashlib,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
results={}
for name in sys.argv[1:]:
 p=root/'tmp/phase8'/('normal-'+name);base=0x880000
 initial=(p/'qual-start.bin').read_bytes();i=initial.find(b'GPCVERIFY\0');assert i>=0
 h=struct.unpack_from('>I',initial,i+10)[0];db=struct.unpack_from('>I',initial,h-base-4)[0]*4+4;a=db+32766-base
 states={}
 for n in ['qual-start','qual-finished','transition','race-start','race-end']:
  d=(p/(n+'.bin')).read_bytes();w=lambda o:struct.unpack_from('>h',d,a+o)[0];l=lambda o:struct.unpack_from('>I',d,a+o)[0]
  origin=l(-16330);end=l(-16326);old=db+0x68ca
  assert origin&65535==65522 and end-origin==1643
  assert d[origin-base-64:end-base+64]==d[old-base-64:old-base+1643+64],n
  grid=[w(3732+2*j) for j in range(10)]
  states[n]=dict(origin=hex(origin),track=w(-31430),speed=w(-29944),player=l(-30016)-origin,camera=l(-30010)-origin,rank=w(-30000),lap=w(-31422),finished=w(3728),time=w(-31416),ai=w(3846),grid=grid,positions_by_grid=[l(6+4*j)-origin for j in grid])
 assert states['qual-start']['track']==6 and states['qual-start']['ai']==0
 assert states['qual-finished']['lap']==2 and states['qual-finished']['finished']==-1
 assert states['transition']['ai']==1 and states['transition']['time']==1
 assert states['race-start']['grid'][0]==0
 assert states['race-start']['player']==states['race-end']['player']==30
 assert states['race-start']['camera']==states['race-end']['camera']==30
 samples=[list(map(int,x.split())) for x in re.findall(r'^STATE (.+)$',(p/'debugger.txt').read_text(),re.M)]
 assert len(samples)==15 and all(x[-1]==0 and x[1]==x[2]==int(states['race-start']['origin'],16)+30 for x in samples)
 assert samples[-1][3]>samples[0][3] # opponent motion while player stays still
 rows=json.loads((p/'draws.json').read_text())
 if 'baseline' in name:
  assert states['race-start']['positions_by_grid']==[30,28,22,21,15,14,65544,65543,65537,65536]
  assert states['race-start']['rank']==5 and len(rows)==0
 else:
  assert states['race-start']['positions_by_grid']==[30,28,22,21,15,14,8,7,1,0]
  assert states['race-start']['rank']==1
  assert len(rows)>100 and len(set(x[1] for x in rows))>=7 and all(x[4]==0 for x in rows)
 results[name]=dict(scope='isolated diagnostic; unchanged Monza bytes relocated to low address fff2, joystick qualifying, forced pole time, native race/grid/start lights',slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),track_copy_exact=True,states=states,stationary_samples=len(samples),front_draws=len(rows),drawn_ids=sorted(set(x[1]//2 for x in rows)))
 print(name,'PASS',len(rows),'front draws')
(root/'tmp/phase8/monza-wrap-report.json').write_text(json.dumps(results,indent=2)+'\n')
