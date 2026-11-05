import os,subprocess,sys,json
from pathlib import Path
from drive import ROOT
root=ROOT/'tmp/b-final-checks';root.mkdir(exist_ok=True)
for name,tool,extra,args in [
 ('keyboard','input_b.py',{},[]),('pad','input_b.py',{'RR_PAD':'1'},[]),
 ('off','replay_a.py',{},['--normal']),('on','replay_a.py',{'WHD_ARGS':'CUSTOM2=3'},['--normal']),
 ('hash','check_a.py',{'SLAVE':str(ROOT/'tmp/b-final-build/RoadRash-verify-hash.slave'),'WHD_ARGS':'CUSTOM2=3'},['--hash'])]:
 env=dict(os.environ,DEBUG_PORT='3096',SLAVE=str(ROOT/'tmp/b-final-build/RoadRash.slave'));env.update(extra)
 with (root/(name+'.log')).open('w') as log:r=subprocess.run([sys.executable,str(ROOT/'tools'/tool),str(root/name)]+args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 print(name,r.returncode,flush=True)
 if r.returncode:raise RuntimeError(name)
