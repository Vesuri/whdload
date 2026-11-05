#!/usr/bin/env python3
"""Single fresh W4 OFF/ON boot: 250 recorded fields and a >=2000-field census."""
import argparse,json,os,re,signal,struct,subprocess,sys,threading
from pathlib import Path
import route_status as r,step_log
p=argparse.ArgumentParser();p.add_argument('--suffix',default='');p.add_argument('machine',choices=['a500','020']);p.add_argument('mask',type=int,choices=[0,128]);a=p.parse_args()
out=Path(f'tmp/prof/w4-{a.machine}-{a.mask}{a.suffix}')
subprocess.run([sys.executable,'tools/w4_boot.py',a.machine,str(a.mask),str(out)],check=True)
m=json.loads((out/'entry.json').read_text());listing=(out/'slave.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
slave=m['entry']['game_anchor']-label('tape_game_anchor');sim=m['entry']['sim']
def advance(target):
 state=r.read(r.locate());remaining=target-state['game_steps'];assert remaining>0
 cmd=f'gdb break *{state["game_anchor"]:#x}\nignore $bpnum {remaining-1}\nbreak *{sim+0x21f4a:#x}'
 r.command(cmd);timer=threading.Timer(55,lambda:os.kill(int(Path('tmp/run/default/.run/gdb.pid').read_text()),signal.SIGINT));timer.start()
 try:reply=r.command('gdb continue')
 finally:timer.cancel()
 r.command('gdb delete');state=step_log.collect()
 if state['count']!=target:raise RuntimeError(f'Checkpoint not reached: {state["count"]}, {reply}')
 return state
state=advance(8);(out/'step8.json').write_text(json.dumps(state,indent=2)+'\n')
r.command(f'gdb dump binary memory {out}/step8-h3.bin {state["h3"]:#x} {state["h3"]+0xbd0c:#x}')
for i,n in enumerate((100,100,50)):
 subprocess.run([sys.executable,'tools/capture_current.py','--out',str(out/f'chunk{i}'),'--fields',str(n)],check=True)
subprocess.run([sys.executable,'tools/w4_costs.py',str(out)],check=True)
for domain,original,base in [('sim','sim',sim)]:
 if domain=='sound' and a.mask:continue
 args=[sys.executable,'tools/check_disabled.py',f'tmp/game/RedBaron/data/{original}','--domain',domain,'--base',str(base),'--custom2',str(a.mask)]
 for memory in sorted((out/'chunk0').glob('memory-*.bin')):args+=['--memory',str(int(memory.stem.split('-')[1],16))+':'+str(memory)]
 subprocess.run(args,check=True)
subprocess.run([sys.executable,'tools/w3_rate.py',a.machine,str(out)],check=True)
end=step_log.collect()
(out/'census.json').write_text(json.dumps(end,indent=2)+'\n');r.command(f'gdb dump binary memory {out}/census-h3.bin {end["h3"]:#x} {end["h3"]+0xbd0c:#x}')
print(r.command('shot '+str((out/'end.png').resolve())))
(out/'complete.json').write_text(json.dumps(dict(complete=True,machine=a.machine,mask=a.mask,sha256=m['slave_sha256'],recorded_fields=250,chunk_gaps=2),indent=2)+'\n')
