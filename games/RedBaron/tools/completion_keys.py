"""Deliver native queue keys after menu polls, using the authorized host driver."""
import argparse,socket,time,os,itertools
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('base',type=lambda s:int(s,0));p.add_argument('module',choices=['ps','sim']);p.add_argument('keys',nargs='+');p.add_argument('--polls',type=int,default=20);a=p.parse_args()
off,bitmap=(0x15b3a,0x2ba5c) if a.module=='ps' else (0x1ef92,0x30f8c)
codes={'return':0x44,'tab':0x42,'right':0x4e,'left':0x4f,'f10':0x59,'esc':0x45,'f1':0x50,'f2':0x51}
groups=[]
for key,items in itertools.groupby(a.keys):
 count=len(list(items))
 if key in ('right','left') and os.environ.get('BENCH_BATCH_KEYS')=='1':
  while count:
   size=min(count,32);groups.append((key,size));count-=size
 else:groups.extend((key,1) for _ in range(count))
for index,(key,repeat) in enumerate(groups):
 r.command('stop')
 r.command(f'gdb delete\nbreak *{a.base+off:#x}\nignore $bpnum {a.polls-1}\ncontinue\ndelete')
 with socket.socket(socket.AF_UNIX) as s:
  s.connect(str(Path('tmp/run/default/.run/completion-input.sock').resolve()));s.sendall((f'burst:{a.base},{bitmap},{codes[key]},{repeat}' if repeat>1 else f'{a.base},{bitmap},{codes[key]}').encode());reply=s.recv(65536).decode();assert reply.startswith('OK'),reply
 print('KEY',a.module,key,'count',repeat,flush=True)
 if os.environ.get('BENCH_BATCH_KEYS')=='1' and a.module=='sim' and len(a.keys)>40 and index==len(groups)-2:
  print(r.command('shot '+str(Path(f'tmp/prof/completion-prefs-{os.getpid()}.png').resolve())),flush=True)
