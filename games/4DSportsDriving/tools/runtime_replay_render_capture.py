#!/usr/bin/env python3
"""Read-only250-state replay comparison window with render/field counters."""
import sys,json,re,struct,hashlib
from pathlib import Path
from runtime_lifecycle_probe import cap,command,m,a,base,s,irq,snapshot
from profile_window import ROOT
label=sys.argv[1];detail=int(sys.argv[2]);assert detail in (0,3)
outdir=cap/label;outdir.mkdir()
before=snapshot(label+'-request');assert before['mode']==2 and before['active_rate']==50 and before['consumer']<1351 and before['detail']==detail,before
raw=(cap/(label+'-request.bin')).read_bytes()
groups=[('CORE',a-0xa80,280,4),('RNG',a+0x228,3,2)]
for name,tag,size in [('PHYS',b'4DA4PHYS',152),('TIME',b'4DTSTATE',32),('AUX',b'4DAUXPHY',192),('CAMERA',b'4DCAM050',8)]:
 assert raw.count(tag)==1,(tag,raw.count(tag))
 groups.append((name,m['memory_base']+raw.index(tag)+12,size//4,4))
lines=['delete','set $render_count=0','set $hit=0',f"break *{m['game_base']+0x7500:#x}",'commands','silent','set $render_count=$render_count+1','continue','end',f"break *{m['game_base']+0xe5f8:#x}",f"condition $bpnum *(unsigned char *){a+0x45:#x}==2",'commands','silent',f'set $tick=*(unsigned short *){a-0x940:#x}','if $tick>=1351 && $tick<=1600',f'printf "STATE %u %u %u\\n", $tick, *(unsigned int *){base+s["sim_clock_fields"]:#x}, $render_count']
for name,addr,count,width in groups:
 lines += [f'printf "GROUP_{name}\\n"',f'x/{count}{"w"if width==4 else"h"}x {addr:#x}']
lines += ['printf "STATE_END\\n"','end','if $tick==1600','set $hit=1','else','continue','end','end',f'break *{irq:#x}',f"condition $bpnum *(unsigned int *){base+s['sim_clock_fields']:#x}>={before['sim_clock_fields']+2200}",'continue','printf "CAPTURE_HIT %u\\n", $hit','delete']
f=outdir/'capture.gdb';f.write_text('\n'.join(lines)+'\n');text=command('gdb source '+str(f.relative_to(ROOT)));(outdir/'capture.log').write_text(text);assert 'CAPTURE_HIT 1'in text,text[-1000:]
rows=[];states=[]
for tick,field,frames,body in re.findall(r'^STATE (\d+) (\d+) (\d+)\n(.*?)^STATE_END$',text,re.M|re.S):
 data=b''
 for name,addr,count,width in groups:
  region=re.search(r'^GROUP_'+name+r'\n(.*?)(?=^GROUP_|\Z)',body,re.M|re.S)[1]
  values=[]
  for line in region.splitlines():
   if re.match(r'^0x[\da-f]+\s*:',line,re.I):values += [int(x,16)for x in re.findall(r'0x[\da-f]+',line.split(':',1)[1],re.I)]
  assert len(values)==count,(name,len(values),count)
  data+=b''.join(v.to_bytes(width,'big')for v in values)
 assert len(data)==1510
 rows.append(dict(tick=int(tick),field=int(field),renders=int(frames),sha256=hashlib.sha256(data).hexdigest()));states.append(data)
assert [r['tick']for r in rows]==list(range(1351,1601))
end=snapshot(label+'-end');assert end['mode']==2 and end['active_rate']==50 and end['detail']==detail and end['perf_failure']==end['sim_schedule_overflow']==0
(outdir/'states.bin').write_bytes(b''.join(states))
r=dict(detail=detail,states=len(states),bytes_per_state=1510,groups=groups,rows=rows,field_span=rows[-1]['field']-rows[0]['field'],render_span=rows[-1]['renders']-rows[0]['renders'],slave_sha256=hashlib.sha256((cap/'start/slave.slave').read_bytes()).hexdigest(),scope='Native replay at matching completed ticks; full native/RNG/ABI9 semantic state. Render marker counts, not DMA-validated displayed FPS. No guest memory writes.')
(outdir/'capture.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k not in ('rows','groups')},indent=2))
