import json,struct,itertools,sys,os
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]);m=json.loads((cap/'anchor.json').read_text());a=m['data_base']+0x7ffe;s=m['clock_symbols']
p=Path('tmp/prof/finish-steering-twins-a500');old=json.loads((p/'anchor.json').read_text());b=(p/'outcome-memory.bin').read_bytes();oa=old['data_base']+0x7ffe-old['memory_base'];ptr=struct.unpack_from('>I',b,oa-0x1770)[0]-old['memory_base'];count=struct.unpack_from('>H',b,oa+0xa0)[0];inputs=b[ptr:ptr+count]
keys={1:0x4c,2:0x4d,4:0x4e,8:0x4f,16:0x20,32:0x31};held=0;rows=[]

def sample_timing():
 q={'fields':(s['sim_clock_fields'],'int'),'consumed':(a-0x940,'short'),'produced':(a+0xa0,'short'),'base':(a-0x2e0,'short'),'clock':(a+0x2342,'int'),'latch':(a-0x217c,'short'),'outcome':(a-0x865,'char'),'opponent':(a-0x174a,'char'),'overflow':(s['sim_schedule_overflow'],'short'),'read':(s['sim_schedule_read'],'short'),'write':(s['sim_schedule_write'],'short'),'failure':(s['perf_failure'],'int')}
 out=command('gdb '+'\n'.join(f'p /u *(unsigned {typ} *){addr:#x}' for addr,typ in q.values()))
 vals=list(map(int,re.findall(r'^\$\d+ = (\d+)',out,re.M)));assert len(vals)==len(q),out
 r=dict(zip(q,vals));assert r['opponent']==1 and r['overflow']==r['failure']==0,r
 r['queue']=(r['write']-r['read'])&65535;r['backlog']=(r['produced']-r['consumed'])&65535
 timing.append(r);(cap/'timing-samples.json').write_text(json.dumps(timing));return r

timing=[]
def field_count():
 out=command(f'gdb p /u *(unsigned int *){s["sim_clock_fields"]:#x}');return int(re.search(r'\$\d+ = (\d+)',out)[1])
import re
start_fields=field_count();command('gdb monitor key 4c 1');crash=[]
for _ in range(30):
 command('gdb monitor fields 50')
 out=command(f'gdb p /u *(unsigned char *){a-0x865:#x}\np /u *(unsigned short *){s["sim_schedule_overflow"]:#x}\np /u *(unsigned int *){s["perf_failure"]:#x}')
 vals=list(map(int,re.findall(r'^\$\d+ = (\d+)',out,re.M)));assert len(vals)==3,out;crash.append(vals);assert vals[1:]==[0,0]
 if vals[0]:break
command('gdb monitor key 4c 0\nmonitor key 4e 0');command('shot '+str(cap/'crash-first.png'));assert crash[-1][0] in (1,2,5),crash
g=m['game_base'];command(f'gdb delete\nbreak *{g+0x9c26:#x}')
menu=False
for _ in range(30):
 for pressed in (1,0):
  command(f'gdb monitor key 44 {pressed}');command('wait 0.15');command('stop')
  regs=command('gdb info registers pc');match=re.search(r'pc\s+0x([0-9a-f]+)',regs)
  if match and int(match[1],16)==g+0x9c26:menu=True;break
 if menu:break
command('gdb monitor key 44 0\ndelete\nstepi');assert menu,'Replay menu entry not reached'
command('gdb monitor fields 100')
for _ in range(2):
 command('gdb monitor key 4d 1\nmonitor fields 15\nmonitor key 4d 0\nmonitor fields 30')
command(f'gdb break *{g+0x7500:#x} if *(unsigned char *){a+0x45:#x}==0 && *(unsigned char *){a-0x865:#x}==0 && *(unsigned short *){a-0x940:#x}<100')
command('gdb monitor key 44 1');command('wait 0.15');command('stop');command('gdb monitor key 44 0')
regs=command('gdb info registers pc');match=re.search(r'pc\s+0x([0-9a-f]+)',regs)
if not match or int(match[1],16)!=g+0x7500:command('gdb continue')
regs=command('gdb info registers pc');match=re.search(r'pc\s+0x([0-9a-f]+)',regs);restarted=bool(match and int(match[1],16)==g+0x7500)
command('gdb monitor key 44 0\ndelete');command('shot '+str(cap/'restart.png'));assert restarted,'Native restart not reached'
for k in [0x44,*keys.values()]:command(f'gdb monitor key {k:x} 0')
for bits,group in itertools.groupby(inputs):
 n=len(list(group))
 if os.environ.get("P5_SHORT")=="1" and n>200:n=10
 if bits==5 and json.loads((cap/'window.json').read_text())['start']['rate']in (20,50):
  import subprocess
  command('gdb monitor key 4c 1')
  subprocess.run(['python3','tools/p5_finish_drive.py',str(cap)],check=True)
  adaptive=json.loads((cap/'finish-check.json').read_text());rows.append(dict(input='adaptive',ticks=None,consumer=adaptive['rows'][-1]['consumer'],outcome=adaptive['outcome'],overflow=adaptive['overflow']));held=0;break
 for bit,k in keys.items():
  if bool(bits&bit)!=bool(held&bit):command(f'gdb monitor key {k:x} {int(bool(bits&bit))}')
 held=bits
 remaining=max(1,n*5-1)
 sample_timing()
 while remaining:
  chunk=min(remaining,1000);command(f'gdb monitor fields {chunk}');remaining-=chunk;sample_timing()
 out=command(f'gdb p /u *(unsigned short *){a-0x940:#x}\np /u *(unsigned char *){a-0x865:#x}\np /u *(unsigned short *){s["sim_schedule_overflow"]:#x}')
 import re
 vals=list(map(int,re.findall(r'^\$\d+ = (\d+)',out,re.M)));assert len(vals)==3,out;rows.append(dict(input=bits,ticks=n,consumer=vals[0],outcome=vals[1],overflow=vals[2]));assert not vals[2]
 if vals[1]:break
for bit,k in keys.items():
 if held&bit:command(f'gdb monitor key {k:x} 0')
command('shot '+str(cap/'recorded-finish.png'))
q=cap/'recorded-final.bin';command(f'gdb dump binary memory {q.relative_to(ROOT)} {a-0xa80:#x} {a-0x620:#x}')
r=dict(rows=rows,outcome=rows[-1]['outcome'],slave_sha256=m['slave_sha256'],scope='Ordinary live keyboard playback of prior successful native finish controls; includes long idle/gear-down prelude, not a combined crash/finish endurance acceptance.')
(cap/'recorded-finish.json').write_text(json.dumps(r,indent=2));print(r,flush=True);assert r['outcome']==3


r.update(crash_observations=crash,restarted=restarted,elapsed_fields=field_count()-start_fields,scope='Same production process: ordinary-key live crash, native menu restart, then native finish using a prior successful input sequence. Includes a long idle/gear-down prelude; not continuous movement. No guest-state writes.')
(cap/'combined-lifecycle.json').write_text(json.dumps(r,indent=2));assert r['elapsed_fields']>=6000 or os.environ.get('P5_SHORT')=='1'
(cap/'timing-samples.json').write_text(json.dumps(timing,indent=2))
segments=[]
for first,last in zip(timing,timing[1:]):
 delta=last['fields']-first['fields']
 if delta<240 or delta>1010 or first['outcome'] or last['outcome']:continue
 ticks=((last['base']+last['consumed'])-(first['base']+first['consumed']))&65535
 secs=(last['clock']-first['clock'])*first['latch']/709379
 segments.append(dict(seconds=secs,ticks=ticks))
secs=sum(x['seconds'] for x in segments);ticks=sum(x['ticks'] for x in segments)
assert secs>60 or os.environ.get('P5_SHORT')=='1',secs
ratio=ticks/50/secs if secs else None
if ratio is not None:assert abs(ratio-1)<=.005,ratio
r.update(diagnostic_short=os.environ.get("P5_SHORT")=="1",clock_ratio=ratio,clock_sample_seconds=secs,queue_max=max(x['queue'] for x in timing),backlog_max=max(x['backlog'] for x in timing),opponent=1)
assert r['queue_max']<=3 and r['backlog_max']<=3,r
(cap/'combined-lifecycle.json').write_text(json.dumps(r,indent=2));print('COMBINED PASS',r['elapsed_fields'],ratio,flush=True)
