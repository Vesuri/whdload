"""Report only completed scene pairs from the frozen W2 matrix."""
import hashlib,json
from pathlib import Path
p=Path('tmp/prof');expected='1456f8d5b84cf787f3429b7ae6580fcc88ce94903d604bbb3d339610f85853b3';result=[]
for cpu,on in [('a500',60),('020',60),('030',56)]:
 for scene in ['bank','dense']:
  paths=[p/f'w2-scene-{cpu}-{scene}-{mask}' for mask in [0,on]]
  if not all((x/'complete.json').exists() for x in paths):
   print('pending',cpu,scene);continue
  for x in paths:
   assert json.loads((x/'complete.json').read_text())['complete']
   assert hashlib.sha256((x/'slave.slave').read_bytes()).hexdigest()==expected
   assert json.loads((x/'entry.json').read_text())['slave_sha256']==expected
  for name in (['event','bank'] if scene=='bank' else ['dense']):
   data=[json.loads((x/(name+'-costs.json')).read_text()) for x in paths]
   key='summaries' if cpu=='030' else 'summary'
   pairs={}
   for routine in sorted(set(data[0][key])&set(data[1][key])):
    vals=[x[key][routine] for x in data]
    pairs[routine]=dict(off=vals[0],on=vals[1])
   display=[]
   for x in paths:
    f=x/name/'display.json'
    if f.exists():
     d=json.loads(f.read_text());display.append(dict(observable=d['observable'],conflicts=len(d['active_display_conflicts'])))
   row=dict(cpu=cpu,scene=name,mask=on,pairs=pairs,display=display)
   if cpu=='030':
    passes=[{r['step']:r['fields']*1000/49.92041 for r in d['accepted'] if r['routine']=='world3d'} for d in data]
    common=sorted(set(passes[0])&set(passes[1]));assert common
    row['common_world_steps']=common
    row['common_world_mean_ms']=[sum(d[k] for k in common)/len(common) for d in passes]
    print('common phase-safe passes',common,row['common_world_mean_ms'])
   result.append(row)
   w=pairs.get('world3d',{});print(cpu,name,w,display)
  if cpu=='a500':
   name=scene+'-before'
   states=[json.loads((x/(name+'.json')).read_text()) for x in paths]
   assert states[0]['count']==states[1]['count']
   buffers=[(x/(name+'-h3.bin')).read_bytes() for x in paths];assert len(buffers[0])==len(buffers[1])
   diff=[i for i,(a,b) in enumerate(zip(*buffers)) if a!=b];groups=[]
   for i in diff:
    if groups and i==groups[-1][-1]+1:groups[-1].append(i)
    else:groups.append([i])
   print('h3 at step',states[0]['count'],'diff ranges',[(hex(x[0]),hex(x[-1]+1)) for x in groups])
(p/'w2-scene-report.json').write_text(json.dumps(result,indent=2)+'\n')
