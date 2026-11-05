#!/usr/bin/env python3
"""Read-only dashboard census with bounded segments and a flight-exit guard.
Drain the 256-entry step ring every 200 steps. A limit/timeout/error is partial.
"""
import argparse,json,re,socket,threading,signal,os,collections
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--step-limit',type=int,default=2000);p.add_argument('--timeout',type=int,default=180);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
at=r.locate();state=r.read(at);obs,h=step_log.header();sim,h3=state['sim'],h[5]
if not state['inflight']:raise SystemExit('Start at a flight checkpoint')
initial=step_log.collect();first=initial['records'][-1];current=first['step'];records={current:first};events=[];ended=False;complete=True
points={'dirty':0x197ee,'full':0x668,'top':0x7de,'message':0x3ba2,'mirror':0x304d0,'reject':0x305c8,'swap':0x3154a}
while current<a.step_limit:
 target=min(current+200,a.step_limit);cmd=[]
 for name,offset in points.items():
  extra='*(unsigned long *)($a0+8)' if name=='mirror' else '0'
  cmd += [f'break *{sim+offset:#x}','commands','silent',f'printf "RB_CENSUS {name} %u %u %u %u %u %u %u\\n", *(unsigned long *){at+44:#x}, *(unsigned long *){obs+36:#x}, *(unsigned long *){sim+0x30006:#x}, $a0, $d0, $d1, {extra}','continue','end']
 cmd += [f'break *{sim+0x21f4a:#x}',f'break *{state["game_anchor"]:#x}',f'ignore $bpnum {target-current-1}','continue',f'printf "RB_CENSUS_STOP %u %u %u\\n", $pc, *(unsigned long *){obs+36:#x}, *(unsigned long *){sim+0x30006:#x}','delete']
 # This is the same harness connection throughout; no process lookup by name.
 pid=int((r.ROOT/'tmp/run/default/.run/gdb.pid').read_text());timer=threading.Timer(a.timeout,lambda:os.kill(pid,signal.SIGINT));timer.start()
 try:
  with socket.socket(socket.AF_UNIX) as sock:
   sock.settimeout(a.timeout+60);sock.connect(str(r.ROOT/'tmp/run/default/.run/redbaron.sock'));sock.sendall(('gdb '+'\n'.join(cmd)).encode());chunks=[]
   while chunk:=sock.recv(65536):chunks.append(chunk)
  reply=b''.join(chunks).decode()
 finally:timer.cancel()
 (a.out/f'to-{target}.txt').write_text(reply)
 rows=[dict(kind=n,step=int(s),vbl=int(v),ticks=int(t),a0=int(p),d0=int(d0),d1=int(d1),dimensions=int(dim)) for n,s,v,t,p,d0,d1,dim in re.findall(r'RB_CENSUS (\w+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',reply)]
 events.extend(rows);end=step_log.collect()
 for row in end['records']:
  if row['step']>=first['step']:records[row['step']]=row
 current=end['records'][-1]['step'];stopped=re.search(r'RB_CENSUS_STOP (\d+) (\d+) (\d+)',reply)
 ended=bool(stopped and int(stopped[1])==sim+0x21f4a)
 complete=bool(stopped and (ended or current==target) and not any(x in reply for x in ['Invalid hex digit','Remote communication error','ERROR']))
 counts=dict(collections.Counter(x['kind'] for x in events));result=dict(first=first,last=end['records'][-1],mission_ended=ended,segment_complete=complete,stop_clock=None if not stopped else dict(vbl=int(stopped[2]),ticks=int(stopped[3])),counts=counts,events=events,records=list(records.values()))
 (a.out/'census.json').write_text(json.dumps(result,indent=2)+'\n');print(dict(step=current,mission_ended=ended,segment_complete=complete,counts=counts),flush=True)
 if ended or not complete:break
if len(records)!=current-first['step']+1:raise SystemExit('Incomplete step history')
if not complete or current!=a.step_limit or ended:raise SystemExit('Requested bounded flight window not completed')
