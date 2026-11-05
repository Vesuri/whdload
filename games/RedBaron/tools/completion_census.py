"""Normal-build external stage/cadence census; no guest instrumentation."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from routine_wall_time import summarize
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--fields',type=int,default=2000);p.add_argument('--window',choices=['event','steady','opening'],required=True);p.add_argument('--stem');a=p.parse_args()
r.command('stop')
m=json.loads((a.capture/'entry.json').read_text());sim=m['sim'];stem=a.capture/(a.stem or a.window)
if a.fields < (250 if m.get('route','').startswith('E1 ') else 1000):raise SystemExit('Window below required field count')
if stem.with_suffix('.json').exists():raise SystemExit('Refuse overwrite')
# Reject an unloaded/replaced executable before installing any wait.
identity=r.command(f'gdb x/3hx {sim+0x1ef92:#x}')
words=re.findall(r'0x[0-9a-f]+',identity.split(':',1)[1])
assert [int(x,16) for x in words[:3]]==[0x4ef9,(sim+0x309cc)>>16,(sim+0x309cc)&65535], 'SIM keyboard entry is no longer resident'
# Native VBlank entry supplies the external field clock for either CUSTOM2 value.
r.command(f'gdb delete\nbreak *{sim+0x2d34e:#x}\ncontinue\ndelete')
spans=[('world',0x1098,0x11c8),('scene',0x6bc,0x7c4),('cockpit',0x7c4,0x830),('publication',0xafe,0xb10)]
if m.get('route','').startswith('E1 '):
 spans += [('instruments',0x15e96,0x163a0),('dispatch',0x19ba6,0x19e12),('three_d',0x2c552,0x2c806)]
points={}
for name,lo,hi in spans:
 points.setdefault(lo,[]).append((name,'enter'));points.setdefault(hi,[]).append((name,'return'))
cmd=['delete','set $field=0','set $step=0']
for off,tags in points.items():
 cmd += [f'break *{sim+off:#x}','commands','silent']
 if off==0x1098:cmd+=['set $step=$step+1']
 for name,kind in tags:cmd += [f'printf "CLOCK {name} {kind} %u %u %u %u\\n", $step, $field, *(unsigned int*)0xdff004, $sp']
 cmd += ['continue','end']
for label,off in ([] if m.get('route','').startswith('E1 ') else [('full',0x668),('top',0x7de),('dirty',0x197ee),('message_erase',0x3ba2)]):
 cmd += [f'break *{sim+off:#x}','commands','silent',f'printf "DASH {label} %u\\n", $field','continue','end']
cmd += [f'break *{sim+0x21f4a:#x}','commands','silent','printf "FLIGHT_EXIT %u\\n", $field','end']
cmd += [f'break *{sim+0x3154a:#x}','commands','silent','printf "PUB %u %u\\n", $field, *(unsigned int*)0xdff004','continue','end',f'break *{sim+0x3c06:#x}','commands','silent','printf "MESSAGE %u\\n", $field','continue','end',f'break *{sim+0x2d34e:#x}','commands','silent','set $field=$field+1','printf "FIELD %u %u\\n", $field, *(unsigned int*)0xdff004',f'if $field < {a.fields}','continue','end','end','continue','delete']
if m.get('route','').startswith('E1 '):
 start=cmd.index(f'break *{sim+0x3c06:#x}')
 del cmd[start:start+6]
 assert sum(line.startswith('break *') for line in cmd)<=16
raw=r.command('gdb '+'\n'.join(cmd));stem.with_suffix('.log').write_text(raw)
phase=[dict(vbl=int(v),beam=int(b),line=(int(b)>>8)&511) for v,b in re.findall(r'^FIELD (\d+) (\d+)$',raw,re.M)]
assert 'FLIGHT_EXIT' not in raw, 'Mission ended during the window'
assert len(phase)==a.fields and phase[-1]['vbl']==a.fields
active={};calls=[]
for name,kind,step,field,beam,sp in re.findall(r'^CLOCK (\w+) (\w+) (\d+) (\d+) (\d+) (\d+)$',raw,re.M):
 row=dict(step=int(step),vbl=int(field),beam=int(beam),sp=int(sp),line=(int(beam)>>8)&511,hpos=int(beam)&255)
 if kind=='enter':
  assert name not in active,name
  active[name]=row
 elif name in active:calls.append(dict(routine=name,entry=active.pop(name),return_record=row))
log=dict(complete=True,vblank_phase=phase,calls=calls)
summary=summarize(log,0,1000000)
pubs=[dict(field=int(f),beam=int(b)) for f,b in re.findall(r'^PUB (\d+) (\d+)$',raw,re.M)]
dashboard={label:len(re.findall(r'^DASH '+label+' ',raw,re.M)) for label in ('full','top','dirty','message_erase')}
result=dict(dashboard=dashboard,**m,window=a.window,fields=a.fields,fps=len(pubs)*49.92041/a.fields,publications=pubs,messages=len(re.findall(r'^MESSAGE ',raw,re.M)),timing=summary,raw=log)
if a.window=='steady' and any(dashboard.values()):result['classification']='event observed; not accepted as steady'
elif a.window=='event' and not any(dashboard.values()):result['classification']='no event observed; not accepted as event'
else:result['classification']='accepted'
stem.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
print(a.window,'FPS',result['fps'],'messages',result['messages'],'dashboard',dashboard,'classification',result['classification'],summary['summaries'],flush=True)
