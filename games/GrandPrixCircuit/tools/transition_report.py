"""Summarize isolated qualifying-to-race diagnostics; never release acceptance."""
import hashlib,json,struct,sys
from pathlib import Path
p=Path(sys.argv[1]);base=0x880000
initial=(p/'qual-start.bin').read_bytes();i=initial.find(b'GPCVERIFY\0')
assert i>=0
h=struct.unpack_from('>I',initial,i+10)[0]
db=struct.unpack_from('>I',initial,h-base-4)[0]*4+4;a=db+32766-base
states={}
for n in ['qual-start','qual-finished','transition','race-start','race-end']:
 d=(p/(n+'.bin')).read_bytes();w=lambda o:struct.unpack_from('>h',d,a+o)[0];l=lambda o:struct.unpack_from('>i',d,a+o)[0]
 states[n]={'track':w(-31430),'car':w(3710),'difficulty':w(-31134),'speed':w(-29944),'position':l(-30016),'fraction':w(-30012),'lap':w(-31422),'finished':w(3728),'time':w(-31416),'ai':w(3846),'grid':[w(3732+2*j) for j in range(10)]}
rows=json.loads((p/'draws.json').read_text())
assert states['qual-start']['track']==6 and states['qual-start']['ai']==0
assert states['qual-finished']['lap']==2 and states['qual-finished']['finished']==-1
assert states['transition']['ai']==1 and states['transition']['time']==1
assert states['race-start']['grid'][0]==0
assert states['race-start']['position']==states['race-end']['position']
assert states['race-start']['fraction']==states['race-end']['fraction']==0
assert rows and all(x[4]==0 for x in rows)
r={'scope':'isolated diagnostic, pilot qualifying and forced pole time', 'native_start_gate': '--native-start' in sys.argv,'slave_sha256':hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),'states':states,'draws':len(rows),'opponents_drawn':sorted(set(x[1]//2 for x in rows)),'x_range':[min(x[2] for x in rows),max(x[2] for x in rows)],'y_range':[min(x[3] for x in rows),max(x[3] for x in rows)],'field_range':[min(x[0] for x in rows),max(x[0] for x in rows)]}
(p/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
