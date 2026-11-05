import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,(name,cell,script,args,extra) in enumerate([('040','040-25','check_a.py',['--normal'],{}),('a500-off','a500-1m','check_a.py',['--normal'],{'WHD_ARGS':'CUSTOM2=0'}),('graphics','040-25','graphics_probe.py',[],{}),('neutral','040-25','visible_latency_c.py',[],{'RR_RIGHT':'0'}),('right','040-25','visible_latency_c.py',[],{'RR_RIGHT':'1'})]):
 env=config(cell);env.update(SLAVE=str(root/'tmp/g-release-build/RoadRash.slave'),DEBUG_PORT=str(28400+i),WHD_ARGS='CUSTOM2=1');env.update(extra);out=root/f'tmp/g-smoke-{name}';out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/'+script,str(out)]+args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 finally:cleanup(out)
 print(name,p.returncode,flush=True);assert not p.returncode
