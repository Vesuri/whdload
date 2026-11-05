import os,sys,subprocess,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path(sys.argv[1]).resolve();root.mkdir(exist_ok=True);results=[]
for i,(name,setup,args,on) in enumerate([('off-default','a1200-fast','',False),('off-explicit','a1200-fast','CUSTOM2=0',False),('on-fast','a1200-fast','CUSTOM2=1',True),('on-68000','a500-1m','CUSTOM2=1',False),('on-chip','a1200','CUSTOM2=1',False)]):
 env=config(setup);env.update(SLAVE=os.environ['SLAVE'],WHD_ARGS=args,RR_RUNTIME_SELECTED=str(int(on)),DEBUG_PORT=str(26382+i))
 out=root/name;out.mkdir();print('starting',name,flush=True)
 with (out/'run.log').open('w') as f:
  p=subprocess.Popen([sys.executable,str(Path(__file__).with_name('runtime_dispatch_c.py')),str(out)],env=env,stdout=f,stderr=subprocess.STDOUT)
  try:rc=p.wait(timeout=240)
  except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=10);rc=-1
  finally:cleanup(out)
 results.append(dict(name=name,returncode=rc));(root/'results.json').write_text(json.dumps(results,indent=2));print(results[-1],flush=True)
 if rc:raise RuntimeError(name)
