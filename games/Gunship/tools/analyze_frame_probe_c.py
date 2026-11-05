from pathlib import Path
import json,struct,sys,re,collections
folder=Path(sys.argv[1]);root=Path(__file__).resolve().parents[1]
listing=(root/'tmp/build/frame-probe.slave.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def frames(tag):
 b=(folder/(tag+'-frames.bin')).read_bytes();assert b[:8]==b'GSFRAME1';count=int.from_bytes(b[8:12],'big');out=[]
 for i in range(max(0,count-511),count):
  x=b[16+(i%512)*48:16+(i%512+1)*48];f,w,start,end=struct.unpack('>4I',x[:16])
  out.append(dict(index=i,field=f,world=w,start=start,end=end,camera=list(struct.unpack('>6H',x[16:28])),packet=list(struct.unpack('>5h',x[28:38])),xyz=list(struct.unpack('>3H',x[38:44]))))
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
