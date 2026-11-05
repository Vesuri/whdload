from pathlib import Path
import json,struct,sys,re,collections
folder=Path(sys.argv[1]);root=Path(__file__).resolve().parents[1]
listing=(root/'tmp/build/scanout-probe.slave.lst').read_text(encoding='latin1')
from functools import lru_cache
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def frames(tag):
 b=(folder/(tag+'-frames.bin')).read_bytes();assert b[:8]==b'GSSCAN01';count=int.from_bytes(b[8:12],'big');out=[]
 for i in range(max(0,count-511),count):
  x=b[16+(i%512)*56:16+(i%512+1)*56];f,w,start,end=struct.unpack('>4I',x[:16])
  out.append(dict(index=i,field=f,world=w,start=start,end=end,camera=list(struct.unpack('>6H',x[16:28])),packet=list(struct.unpack('>5h',x[28:38])),xyz=list(struct.unpack('>3H',x[38:44])),plane0=int.from_bytes(x[48:52],'big')))
 return out
before=frames('before');after=frames('after');rows=[r for r in after if r['index']>before[-1]['index']]
assert rows
assert all(r['end']>=r['start']>=r['field'] for r in rows)
assert all(b['start']>=a['end'] and b['world']>=a['world'] for a,b in zip(rows,rows[1:]))
arena=(folder/'after-arena.bin').read_bytes();rate=int.from_bytes(arena[sym('RT_CLOCK')+22:sym('RT_CLOCK')+24],'big')
changes=[(a['index'],b['index']) for a,b in zip(rows,rows[1:]) if a['world']==b['world'] and a['camera']!=b['camera']]
inputs=[]
for j,event in enumerate(json.loads((folder/'events.json').read_text())):
 a=(folder/f'pulse-{j}-arena.bin').read_bytes();h=a[sym('RT_HISTORY'):];write,read=struct.unpack('>HH',h[:4]);samples=[]
 for i in range(128):
  q=h[20+i*40:20+(i+1)*40];field,x,y=struct.unpack('>Iii',q[:12])
  if event['before']<field<=event['after']:samples.append(dict(field=field,x=x,y=y))
 inputs.append(dict(event=event,samples=sorted(samples,key=lambda r:r['field'])))
responses=[]
for pulse in inputs:
 nz=[s for s in pulse['samples'] if s['x']]
 if not nz:continue
 first=nz[0]['field'];prior=[f for f in after if f['field']<first]
 if not prior:continue
 baseline=prior[-1]['camera'][5]
 changed=[f for f in rows if first<=f['field']<=pulse['event']['after'] and f['camera'][5]!=baseline]
 assert changed,(pulse['event'],'no completed roll response')
 frame=changed[0]
 responses.append(dict(first_input_field=first,last_input_field=nz[-1]['field'],frame_consumed_field=frame['field'],frame_end=frame['end'],delay_fields=frame['end']-first,prior_roll=baseline,roll=frame['camera'][5]))
result=dict(rate=rate,responses=responses,completed_frames=len(rows),field_span=rows[-1]['end']-rows[0]['end'],same_world_camera_changes=len(changes),
 frame_age_fields=[r['end']-r['field'] for r in rows],draw_fields=[r['end']-r['start'] for r in rows],packet_x_counts=dict(collections.Counter(r['packet'][0] for r in rows)),
 frames=rows,input_samples=inputs,display_scanout_measured=False)
(folder/'frame-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k not in ['frames','input_samples','frame_age_fields','draw_fields','responses']})
print('frame ages',min(result['frame_age_fields']),max(result['frame_age_fields']),'draw durations',min(result['draw_fields']),max(result['draw_fields']))
for row in inputs:print(row['event'],'nonzero',[(s['field'],s['x'],s['y']) for s in row['samples'] if s['x'] or s['y']])

from amigaxdev import barto
base=json.loads((folder/'addresses.json').read_text())['base']
scan=[]
for path in sorted(folder.glob('pulse-*.trace')):
 t=barto.load(path)
 event=inputs[int(path.name.split('-')[1])]['event']
 end=event['release'] if '-held.' in path.name else event['after']
 for f in t.fields:
  stamps=[regs[1] for pc,cost,regs in t.instructions(f) if pc==base+sym('history_publish')+22]
  anchored=end-len(t.fields)+1+f.index
  assert not stamps or stamps==[anchored],(path,f.index,stamps,anchored)
  stamps=stamps or [anchored]
  reads=[(i//f.dma_size,struct.unpack_from('<I',f.dma,i+12)[0]) for i in range(0,len(f.dma),f.dma_size) if struct.unpack_from('<h',f.dma,i+29)[0]==6 and struct.unpack_from('<H',f.dma,i)[0]==0x110]
  assert reads
  plane=min(addr for pos,addr in reads)
  assert sorted(addr for pos,addr in reads)==list(range(plane,plane+8000,2)),(path,f.index,"mixed or incomplete plane")
  scan.append(dict(field=stamps[0],plane0=plane,first_line=reads[0][0]//227,last_line=reads[-1][0]//227,reads=len(reads)))
scan.sort(key=lambda x:x['field'])
responses=[]
for pulse in inputs:
 nz=[s for s in pulse['samples'] if s['x']]
 first=nz[0]['field'];prior=[f for f in after if f['field']<first][-1]
 changed=[f for f in rows if first<=f['field']<=pulse['event']['after'] and f['camera'][5]!=prior['camera'][5]][0]
 # The completed record names the buffer drawn. Match only its next scanout,
 # before the following completed frame can reuse that same buffer.
 matches=[s for s in scan if changed['end']<=s['field']<=changed['end']+2 and s['plane0']==changed['plane0']]
 assert matches,(changed,'missing next scanout')
 shown=matches[0]
 previous=[s for s in scan if s['field']<shown['field']]
 assert previous and previous[-1]['plane0']!=shown['plane0'],(changed,'not first buffer transition')
 assert shown['field']-previous[-1]['field']<=2
 earliest=previous[-1]['field']+1
 assert shown['reads']==4000 and shown['last_line']-shown['first_line']==199
 responses.append(dict(first_input=first,frame_index=changed['index'],completion=changed['end'],scanout=shown['field'],delay_fields=shown['field']-first,delay_bounds=[earliest-first,shown['field']-first],plane0=hex(shown['plane0'])))
result['display_scanout_measured']=True
result['scanout']=scan;result['scanout_responses']=responses
(folder/'scanout-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('SCANOUT',responses)
